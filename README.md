# 🤖 Perso AI Chatbot

_Q&A.xlsx + Vector DB(Qdrant) + Gemini Embedding 기반 지식 챗봇_

<p align="center">
  <img src="./public/screenshot.png" alt="Perso AI Chatbot UI" style="max-width:100%;height:auto;" />
</p>

---

## 1. 프로젝트 개요

- **과제 주제**  
  벡터 데이터베이스(Vector DB)를 활용한 지식기반 챗봇 시스템 구축

- **과제 목표**
  - 제공된 `Q&A.xlsx`를 기반으로  
    **할루시네이션 없이** 정확한 응답을 제공하는 챗봇 구현
  - Q&A 데이터셋을 활용해 **벡터 임베딩·검색·질의응답 흐름** 직접 설계
  - ChatGPT / Claude와 유사한 **웹 기반 채팅 UI** 제공

- **핵심 원칙**
  - 답변은 항상 엑셀에 실제 존재하는 **answer 텍스트만 그대로 반환**
  - 데이터에 없는 질문은 **일관되게 “모르겠다”** 로 응답

- **프로젝트 구조**

```text
perso-ai-chatbot/
├── backend/
│   ├── main.py             # FastAPI 엔드포인트
│   ├── embedding.py        # 임베딩 & 어휘 유사도 로직
│   ├── qdrant_service.py   # Qdrant 검색 로직
│   ├── qa_cache.py         # LRU 캐시 (정확 일치)
│   ├── load_xlsx.py        # Q&A.xlsx → Qdrant 적재
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/ChatPage.tsx  # 채팅 UI
│   │   ├── lib/api.ts          # 백엔드 API 호출
│   │   └── App.tsx
│   └── package.json
├── docker-compose.yml         # Qdrant 컨테이너 설정
└── .env                       # 환경변수
```

---

## 2. 사용 기술 스택 ⚙️

### 2.1 Backend

- **FastAPI (Python)**  
  - 비동기 성능, 자동 Swagger 문서 제공
- **Google Gemini API – `text-embedding-004`**
  - 한국어 포함 다국어 지원 우수  
  - `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` task type 으로 검색 최적화
- **Qdrant (Vector DB)**
  - 코사인 유사도 기반 벡터 검색에 최적화  
  - 가볍고 빠른 오픈소스 벡터 데이터베이스
- **Pandas + OpenPyXL** : `Q&A.xlsx` 데이터 로딩 / 전처리
- **Uvicorn** : FastAPI ASGI 서버 실행

### 2.2 Frontend

- **React 19 + TypeScript**
- **Vite** : 빠른 번들링 & HMR(Hot Module Replacement)
- **Tailwind CSS** : 퍼플 & 화이트 톤의 ChatGPT/Claude 스타일 채팅 UI

### 2.3 Infrastructure

- **Docker + Docker Compose**
- **Qdrant 컨테이너 (포트 6333)**  
  → 로컬/서버 환경에서 동일한 벡터 DB 구성 가능

---

## 3. 벡터 DB 및 임베딩 방식 🔍

### 3.1 임베딩 생성 모델: Google Gemini `text-embedding-004`

- **문서 임베딩**  
  엑셀 Q&A의 질문에 대해 `task_type = RETRIEVAL_DOCUMENT`
  
- **쿼리 임베딩**  
  사용자 질문에 대해 `task_type = RETRIEVAL_QUERY`
  
- **비대칭 검색 최적화**  
  문서/쿼리 task type을 분리해 "저장된 질문 ↔ 사용자 질문" 비대칭 검색 성능을 최적화

### 3.2 Qdrant 벡터 DB

- **Distance metric** : COSINE
- **벡터 차원** : 768 (Gemini 기본 차원)
- **Collection 구조 예시**
  ```json
  {
    "id": 1,
    "vector": [0.01, 0.02, "..."],
    "payload": {
      "question": "엑셀 질문",
      "answer": "엑셀 답변",
      "source": "xlsx"
    }
  }
  ```
- **검색 전략**  
  limit = 20 으로 상위 20개 후보를 가져온 뒤 백엔드에서 하이브리드 재랭킹을 수행

---

## 4. 정확도 향상 & 할루시네이션 방지 전략 🎯

### 4.1 3단계 매칭 파이프라인

#### Level 1 – Exact Match (정확 일치)

- `qa_cache.py`에서 정규화된 질문 문자열을 키로 갖는 LRU 캐시 사용
- 사용자의 질문이 엑셀 질문과 완전히 동일하면 → 벡터 검색 없이 즉시 해당 answer 반환 (score = 1.0)

#### Level 2 – Strong Lexical Match (강한 어휘 유사)

- 자체 정의한 `lexical_similarity` 값이 0.6 이상이면 → Qdrant 벡터 점수 / threshold 를 무시하고 해당 Q&A answer 바로 사용
- 말투·어미만 다른 질문을 안정적으로 커버

#### Level 3 – Hybrid Ranking (하이브리드 재랭킹)

- 나머지 후보들에 대해:
  - 벡터 유사도: `vec_score`
  - 어휘 유사도: `lex_score`
  - 조합 스코어: `score = 0.4 * vec_score + 0.6 * lex_score`
- best lexical 근처 ±0.2 범위 후보만 대상으로 재랭킹 → 노이즈 감소
- 최종 스코어가 SCORE_THRESHOLD (예: 0.55, 상한 0.6) 이상인 경우에만 답변 반환

### 4.2 정교한 어휘 유사도 계산

- **Stopwords 제거**: 의문사, 어미, 조사, 공손 표현 
- **도메인 키워드 정규화**: Perso.ai 특화 단어 매핑
- **최종 계산**: Jaccard 유사도(70%) + SequenceMatcher(30%) 조합

### 4.3 환각(Hallucination) 방지 메커니즘

#### 어휘 유사도 하한선

- `lexical < 0.15` → Q&A와 의미가 완전히 다른 질문으로 판단
- 서버 위치 / 출시일 / 정확한 가격 등 데이터에 없는 정보 요청을 항상 아래 메시지로 처리:
  ```
  죄송해요, 제공된 Q&A 데이터에서 해당 질문에 대한 답변을 찾지 못했어요.
  ```

#### Threshold 캡핑

- `effective_threshold = min(SCORE_THRESHOLD, 0.6)`
- 환경 변수 오설정으로 threshold가 과도하게 높아져 모든 질문에 "모르겠다"가 나오는 상황을 예방

#### LLM 답변 생성 없음

- LLM(Gemini)은 **임베딩 생성에만 사용**
- 실제 응답은 항상 엑셀의 `answer` 컬럼 텍스트만 그대로 사용
- LLM이 새로운 문장을 지어내며 발생하는 할루시네이션을 **원천 차단**

---

## 5. 로컬 실행 방법 🚀

### 5.1 사전 준비

- Python 3.11
- Node.js 18+
- Docker / Docker Desktop
- Google Gemini API Key (Google AI Studio에서 발급)

### 5.2 `.env` 설정

프로젝트 루트(`perso-ai-chatbot/`)에 `.env` 생성:

```env
# Google Gemini
GEMINI_API_KEY=YOUR_GEMINI_KEY

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Collection
QDRANT_COLLECTION=perso_qa

# Embedding
EMBEDDING_MODEL=text-embedding-004

# 검색 threshold (0.5~0.6 권장)
SCORE_THRESHOLD=0.5
```

### 5.3 Qdrant 실행

```bash
# 프로젝트 루트에서
docker compose up -d qdrant
```

### 5.4 백엔드 실행

```bash
cd backend

# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt

# 1) Q&A.xlsx → 임베딩 → Qdrant 적재
python load_xlsx.py

# 2) FastAPI 서버 실행
uvicorn main:app --reload --port 8000
# → http://localhost:8000/docs 에서 API 테스트 가능
```

### 5.5 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```