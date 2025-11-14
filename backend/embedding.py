# backend/embedding.py
from typing import List, Literal

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, EMBEDDING_MODEL

# Gemini 클라이언트
client = genai.Client(api_key=GEMINI_API_KEY)

TaskType = Literal[
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
    "RETRIEVAL_DOCUMENT",
    "RETRIEVAL_QUERY",
    "CODE_RETRIEVAL_QUERY",
    "QUESTION_ANSWERING",
    "FACT_VERIFICATION",
]


def _embed(texts: List[str], task_type: TaskType) -> List[list[float]]:
    if not isinstance(texts, list):
        texts = [texts]

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )

    # texts 개수만큼 embedding 이 나옴
    return [e.values for e in result.embeddings]


def embed_documents(texts: List[str]) -> List[list[float]]:
    """코퍼스(엑셀 Q 들)용 임베딩: RETRIEVAL_DOCUMENT"""
    return _embed(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """사용자 질문용 임베딩: RETRIEVAL_QUERY"""
    return _embed([text], task_type="RETRIEVAL_QUERY")[0]
