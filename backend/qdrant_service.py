# backend/qdrant_client.py
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

# Qdrant 클라이언트 생성 :contentReference[oaicite:4]{index=4}
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY or None,
)


def recreate_qa_collection(vector_size: int) -> None:
    """
    기존 컬렉션을 삭제 후, 주어진 vector_size로 새로 생성.
    데모/개발 환경에서만 사용하는 걸 권장 (데이터 다 날림). :contentReference[oaicite:5]{index=5}
    """
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,  # 코사인 유사도
        ),
    )


def upsert_qa_points(
    vectors: List[list[float]],
    questions: List[str],
    answers: List[str],
) -> None:
    """
    Q&A 벡터와 payload(question, answer)를 한 번에 upsert.
    """
    points = []
    for idx, (vec, q, a) in enumerate(zip(vectors, questions, answers), start=1):
        points.append(
            PointStruct(
                id=idx,
                vector=vec,
                payload={
                    "question": q,
                    "answer": a,
                    "source": "xlsx",
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )


def search_similar(query_vector: list[float], limit: int = 3):
    """
    질의 벡터로 유사한 Q&A 점들을 검색. :contentReference[oaicite:6]{index=6}
    """
    return client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=limit,
    )
