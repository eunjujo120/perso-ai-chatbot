# backend/main.py
from typing import Optional
from difflib import SequenceMatcher
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import SCORE_THRESHOLD
from embedding import embed_query
from qdrant_service import search_similar
from qa_cache import find_exact_answer


app = FastAPI(
    title="Perso AI Chatbot",
    description="Q&A.xlsx 기반 지식 챗봇 (Vector DB + Gemini Embedding + Qdrant)",
    version="0.7.0",
)

# 프론트엔드(Vite)와 통신을 위해 CORS 전체 허용 (과제/데모용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========= 요청 / 응답 모델 =========


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    matched_question: Optional[str] = None
    score: Optional[float] = None  # 최종 하이브리드 점수


# ========= 유사도 계산 유틸 =========

# 질문 의미에 거의 기여하지 않는 토큰들
STOPWORDS: set[str] = {
    "perso.ai",
    "persoai",
    # 의문사 / 말투
    "어떤",
    "어떻게",
    "무엇",
    "뭐야",
    "뭐니",
    "뭐하는",
    "알려줘",
    "설명해줘",
    "말해줘",
    "해줘",
    "해주세요",
    "해줘요",
    "좀",
    "조금",
    "요",
    # 서술/의문 끝 어미
    "인가요",
    "인가",
    "입니까",
    "예요",
    "에요",
    # 기타 의미 약한 단어들
    "방법",
    "정도",
    "필요",
    "필요한",
    "필요해",
    "이용하려면",
    "초보",
    "수",
    "있어",
}


def _normalize_base(text: str) -> str:
    """소문자화 + 특수문자 제거 + 공백 정규화."""
    if text is None:
        return ""
    text = text.strip().lower()
    text = text.replace("perso.ai", " ")
    text = re.sub(r"[？?!,\.]", " ", text)  # 주요 문장부호 제거
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_keyword(tok: str) -> str:
    """
    도메인 키워드를 공통 형태로 정규화.
    13개 Q&A에 맞춰 '서비스/기능/기술/고객/회사/회원가입/문의/요금제/영상/편집' 등
    핵심 개념을 동일 토큰으로 만들기 위한 맵핑.
    """
    t = tok

    # 문의 / 고객센터
    if "고객센터" in t:
        return "문의"
    if "문의" in t or "연락" in t:
        return "문의"

    # 서비스 / 기능 / 기술 / 강점
    if "서비스" in t:
        return "서비스"
    if "기능" in t or "기능들" in t in t:
        return "기능"
    if "기술" in t:
        return "기술"
    if "강점" in t or "장점" in t or "경쟁력" in t:
        return "강점"

    # 고객 / 사용자
    if "타깃" in t or "타겟" in t:
        return "고객"
    if "고객층" in t:
        return "고객"
    if "고객" in t:
        return "고객"
    if "사용자" in t or "이용자" in t or "이용자 수" in t or "사람" in t:
        return "사용자"

    # 회사 / 개발사
    if "회사" in t or "기업" in t or "개발사" in t:
        return "회사"
    if "만들" in t or "만든" in t or "개발" in t:
        return "개발"

    # 언어 / 요금 / 가입 / 영상 / 편집
    if "언어" in t:
        return "언어"
    if "요금" in t or "가격" in t or "플랜" in t or "구독" in t:
        return "요금제"
    if "가입" in t:
        return "회원가입"
    if "영상" in t or "비디오" in t:
        return "영상"
    if "편집" in t:
        return "편집"

    # 사용 / 쓰다
    if "쓰" in t or "쓸" in t:
        return "사용"
    if "사용" in t:
        return "사용"

    return t


def _tokenize_for_similarity(text: str) -> list[str]:
    """
    질문 비교용 토큰화:
    - 기본 정규화
    - 어미/조사 제거 (대략적인 규칙)
    - stopword 제거
    - 도메인 키워드 정규화
    """
    base = _normalize_base(text)
    if not base:
        return []

    tokens = base.split()
    cleaned: list[str] = []

    for tok in tokens:
        # 의문/종결 어미 제거
        tok = re.sub(
            r"(인가요|인가|입니까|에요|예요|어요|나요|가요|습니까|죠|야|이야|이니|니)$",
            "",
            tok,
        )
        # 조사 제거 (의는 그대로 두고, 나머지 대표 조사만 제거)
        tok = re.sub(
            r"(은|는|이|가|을|를|에|에서|으로|로|도|만|까지|부터)$",
            "",
            tok,
        )

        tok = tok.strip()
        if not tok:
            continue
        if tok in STOPWORDS:
            continue

        tok = _normalize_keyword(tok)

        if tok and tok not in STOPWORDS:
            cleaned.append(tok)

    # "할 수 있" 패턴은 기능/가능 여부 질문으로 취급
    if "할 수 있" in base:
        cleaned.append("기능")

    return cleaned


def lexical_similarity(a: str, b: str) -> float:
    """
    단어 기반 + 문자 기반을 섞은 문자열 유사도 (0~1).
    - 핵심 단어들의 Jaccard 유사도
    - SequenceMatcher로 미세 조정
    """
    ta = _tokenize_for_similarity(a)
    tb = _tokenize_for_similarity(b)

    if not ta or not tb:
        return 0.0

    set_a, set_b = set(ta), set(tb)
    inter = len(set_a & set_b)
    union = len(set_a | set_b) or 1
    jaccard = inter / union

    seq = SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()

    return 0.7 * jaccard + 0.3 * seq


# 하이브리드 및 임계값 
LEXICAL_STRONG_MATCH = 0.6       # 이 이상이면 "거의 같은 질문"으로 간주
MIN_LEXICAL_FOR_ANY_ANSWER = 0.15  # 이보다 낮으면 완전 다른 질문 → 모르겠다
LEXICAL_NEIGHBOR_MARGIN = 0.2      # best lexical 근처 후보만 재랭킹
VEC_WEIGHT = 0.4                   # 벡터 40% + 문자열 60%


# ========= 엔드포인트 =========


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_q = req.question

    # 0) 엑셀 질문과 완전히 동일하면 바로 반환
    exact_q, exact_a = find_exact_answer(user_q)
    if exact_a is not None:
        return ChatResponse(
            answer=exact_a,
            matched_question=exact_q,
            score=1.0,
        )

    # 1) 임베딩 계산
    try:
        query_vec = embed_query(user_q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    # 2) Qdrant 검색 (데이터 13개라 limit 20이면 사실상 전체)
    try:
        hits = search_similar(query_vec, limit=20)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search error: {e}")

    if not hits:
        return ChatResponse(
            answer="죄송해요, 제공된 Q&A 데이터에서 해당 질문에 대한 답변을 찾지 못했어요.",
            matched_question=None,
            score=None,
        )

    # 3) 후보별 vec_score + lex_score 계산
    candidates = []
    for h in hits:
        payload = h.payload or {}
        cand_q = payload.get("question")
        cand_a = payload.get("answer")
        if not cand_q or not cand_a:
            continue

        vec_score = float(h.score or 0.0)  # Qdrant cosine score
        lex_score = lexical_similarity(user_q, cand_q)

        candidates.append(
            {
                "hit": h,
                "question": cand_q,
                "answer": cand_a,
                "vec_score": vec_score,
                "lex_score": lex_score,
            }
        )

    if not candidates:
        return ChatResponse(
            answer="죄송해요, 제공된 Q&A 데이터에서 해당 질문에 대한 답변을 찾지 못했어요.",
            matched_question=None,
            score=None,
        )

    # 3-1) 문자열 기준으로 가장 비슷한 질문
    best_by_lex = max(candidates, key=lambda c: c["lex_score"])
    best_lex = best_by_lex["lex_score"]

    # 완전히 동떨어진 질문이면 바로 "모르겠다" (환각 방지)
    if best_lex < MIN_LEXICAL_FOR_ANY_ANSWER:
        return ChatResponse(
            answer="죄송해요, 제공된 Q&A 데이터에서 해당 질문에 대한 답변을 찾지 못했어요.",
            matched_question=None,
            score=best_lex,
        )

    # 말투/어미만 다른 "거의 같은 질문"이면 벡터/threshold 무시하고 바로 답변
    if best_lex >= LEXICAL_STRONG_MATCH:
        return ChatResponse(
            answer=best_by_lex["answer"],
            matched_question=best_by_lex["question"],
            score=best_lex,
        )

    # 3-2) 그 외에는 best_lex 근처 후보만 대상으로 하이브리드 재랭킹
    neighbor_candidates = [
        c for c in candidates if c["lex_score"] >= best_lex - LEXICAL_NEIGHBOR_MARGIN
    ]

    best_hit = None
    best_score = -1.0

    for c in neighbor_candidates:
        combined = VEC_WEIGHT * c["vec_score"] + (1.0 - VEC_WEIGHT) * c["lex_score"]
        if combined > best_score:
            best_score = combined
            best_hit = c

    # 너무 높은 threshold가 들어와도 0.6까지만 쓰도록 캡핑
    effective_threshold = min(SCORE_THRESHOLD, 0.6)

    # 4) threshold 아래면 "모르겠다"
    if best_hit is None or best_score < effective_threshold:
        return ChatResponse(
            answer="죄송해요, 제공된 Q&A 데이터에서 해당 질문에 대한 답변을 찾지 못했어요.",
            matched_question=None,
            score=best_score if best_hit is not None else None,
        )

    # 5) 최종적으로 Q&A answer 원문만 반환 
    return ChatResponse(
        answer=best_hit["answer"],
        matched_question=best_hit["question"],
        score=best_score,
    )
