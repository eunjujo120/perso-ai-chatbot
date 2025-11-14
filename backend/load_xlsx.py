# backend/load_xlsx.py
import sys

import pandas as pd

from config import BASE_DIR
from embedding import embed_documents
from qdrant_service import recreate_qa_collection, upsert_qa_points

# 엑셀 파일 경로 (backend/data/Q&A.xlsx)
DATA_PATH = BASE_DIR / "data" / "Q&A.xlsx"

# 엑셀 헤더(1행)에 들어있는 컬럼명
QUESTION_COL = "question"
ANSWER_COL = "answer"


def main():
    # 1) 엑셀 파일 존재 확인
    if not DATA_PATH.exists():
        print(f"[ERROR] 엑셀 파일을 찾을 수 없습니다: {DATA_PATH}")
        sys.exit(1)

    print(f"[INFO] Loading Excel: {DATA_PATH}")
    df = pd.read_excel(DATA_PATH)

    # 2) 컬럼명 확인
    if QUESTION_COL not in df.columns or ANSWER_COL not in df.columns:
        print("[ERROR] 엑셀 컬럼명을 확인하세요.")
        print(f"현재 컬럼들: {list(df.columns)}")
        print(
            f"스크립트에서는 QUESTION_COL={QUESTION_COL}, "
            f"ANSWER_COL={ANSWER_COL} 로 가정하고 있습니다."
        )
        sys.exit(1)

    # 3) 질문/답변 리스트로 추출
    raw_questions = df[QUESTION_COL].astype(str).tolist()
    raw_answers = df[ANSWER_COL].astype(str).tolist()

    # 공백/NaN 제거 + 양쪽 공백 제거
    qa_pairs: list[tuple[str, str]] = []
    for q, a in zip(raw_questions, raw_answers):
        q = (q or "").strip()
        a = (a or "").strip()
        if not q or not a:
            continue
        qa_pairs.append((q, a))

    if not qa_pairs:
        print("[ERROR] 유효한 Q/A 쌍이 없습니다. 엑셀 내용을 확인하세요.")
        sys.exit(1)

    questions = [q for q, _ in qa_pairs]
    answers = [a for _, a in qa_pairs]

    print(f"[INFO] 추출된 Q/A 개수: {len(questions)}")

    # 4) 질문 텍스트 임베딩 생성 (Gemini)
    print("[INFO] 질문 텍스트 임베딩 생성 중 (Gemini)...")
    vectors = embed_documents(questions)
    if not vectors:
        print("[ERROR] 임베딩 결과가 비어 있습니다.")
        sys.exit(1)

    vector_size = len(vectors[0])
    print(f"[INFO] 벡터 차원 수: {vector_size}")

    # 5) Qdrant 컬렉션 재생성 (기존 데이터 초기화)
    print("[INFO] Qdrant 컬렉션 recreate (데이터 초기화 후 재생성)...")
    recreate_qa_collection(vector_size)

    # 6) Qdrant 에 벡터 + Q/A 업로드
    print("[INFO] Qdrant 에 포인트 upsert 중...")
    upsert_qa_points(vectors, questions, answers)

    print("[DONE] Qdrant 에 Q&A 데이터 업로드 완료!")


if __name__ == "__main__":
    main()
