import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# 루트(.env) 로드 (로컬 개발용)
ROOT_ENV = BASE_DIR.parent / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV)

# ===== Gemini / Embedding =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY 가 설정되어 있지 않습니다. .env 파일을 확인하세요.")

# 기본값은 text-embedding-004 로 설정 (원하면 .env에서 변경)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# ===== Qdrant =====
# 로컬에서 load_xlsx.py 를 돌릴 땐 보통 localhost:6333 을 쓰는 게 편함
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # 보통 로컬 도커에선 필요 없음

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "perso_qa")

# ===== 검색 관련 튜닝 =====
# Qdrant 점수 threshold (COSINE 기준 0~1 정도, 높을수록 유사)
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.5"))
