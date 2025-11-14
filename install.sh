#!/usr/bin/env bash
set -e

echo "=== 1) Backend Python 환경 설정 ==="
cd backend

python -m venv .venv
# macOS / Linux 기준 (Windows는 .venv\Scripts\activate)
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

deactivate
cd ..

echo "=== 2) Frontend npm 설치 ==="
cd frontend
npm install
cd ..

echo "=== 3) Docker 이미지 준비 (qdrant, backend) ==="
docker compose pull || true

echo "=== 초기 세팅 완료! ==="
echo "Docker 서비스 실행: docker compose up -d"
echo "백엔드 로컬 실행(옵션):"
echo "  cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo "프론트엔드 로컬 실행:"
echo "  cd frontend && npm run dev"
