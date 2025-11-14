@echo off
echo === 1) Backend Python 환경 설정 ===

cd backend

REM 가상환경 생성
python -m venv .venv

REM 가상환경 활성화
call .venv\Scripts\activate.bat

REM 패키지 설치
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 가상환경 비활성화
deactivate

cd ..

echo === 2) Frontend npm 설치 ===
cd frontend
npm install
cd ..

echo === 3) Docker 이미지 준비 (qdrant, backend) ===
docker compose pull

echo === 초기 세팅 완료! ===
echo * Docker 서비스 실행: docker compose up -d
echo * 백엔드 로컬 실행: 
echo     cd backend ^&^& .venv\Scripts\activate.bat ^&^& uvicorn main:app --reload
echo * 프론트엔드 로컬 실행:
echo     cd frontend ^&^& npm run dev

pause
