# backend/qa_cache.py
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Tuple, Optional
import re

import pandas as pd

from config import BASE_DIR

DATA_PATH = BASE_DIR / "data" / "Q&A.xlsx"
QUESTION_COL = "question"
ANSWER_COL = "answer"


def _normalize(text: str) -> str:
    """질문 비교용 정규화: 공백, ?, !, . 제거 + 소문자."""
    if text is None:
        return ""
    text = text.strip().lower()
    text = re.sub(r"[？?!.]", "", text)
    text = re.sub(r"\s+", "", text)
    return text


@lru_cache(maxsize=1)
def _load_qa_pairs() -> Tuple[Tuple[str, str], ...]:
    """엑셀에서 (질문, 답변) 쌍 전체 로드."""
    if not DATA_PATH.exists():
        return tuple()

    df = pd.read_excel(DATA_PATH)
    if QUESTION_COL not in df.columns or ANSWER_COL not in df.columns:
        return tuple()

    qs = df[QUESTION_COL].astype(str).tolist()
    ans = df[ANSWER_COL].astype(str).tolist()

    pairs = []
    for q, a in zip(qs, ans):
        q = (q or "").strip()
        a = (a or "").strip()
        if not q or not a:
            continue
        pairs.append((q, a))

    return tuple(pairs)


@lru_cache(maxsize=1)
def _exact_map() -> Dict[str, Tuple[str, str]]:
    """정규화된 질문 텍스트 -> (원본질문, 답변) 맵."""
    mapping: Dict[str, Tuple[str, str]] = {}
    for q, a in _load_qa_pairs():
        key = _normalize(q)
        mapping[key] = (q, a)
    return mapping


def find_exact_answer(user_question: str) -> Tuple[Optional[str], Optional[str]]:
    """
    사용자가 친 질문이 엑셀에 있는 질문과 거의 동일하면
    (원본질문, 답변) 을 반환. 없으면 (None, None).
    """
    key = _normalize(user_question)
    pair = _exact_map().get(key)
    if not pair:
        return None, None
    return pair  # (matched_question, answer)
