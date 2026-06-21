import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .diagnose_router import router as diagnose_router
from .sync_router import router as sync_router
from .pdf_service import router as pdf_router
from .training_router import router as training_router
from .ncpms_router import router as ncpms_router

# 앱 시작 시 데이터베이스 초기화
init_db()

app = FastAPI(
    title="AITreeDoctor API",
    description="AI 기반 디지털 수목 진단 및 처방 플랫폼 백엔드 API",
    version="1.0.0"
)

# CORS 설정 (Next.js 프론트엔드 연동 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실무에서는 ["http://localhost:3000"] 등 특정 도메인 지정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 바인딩
app.include_router(diagnose_router, prefix="/api/v1", tags=["수목 진단"])
app.include_router(sync_router, prefix="/api/v1", tags=["농약 동기화"])
app.include_router(pdf_router, prefix="/api/v1", tags=["처방전 PDF"])
app.include_router(training_router, prefix="/api/v1", tags=["AI 모델 학습"])
app.include_router(ncpms_router, prefix="/api/v1", tags=["NCPMS 연동"])

# 정적 파일 서빙 설정 (생성된 PDF 리포트 노출)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 프론트엔드 정적 파일 서빙 설정 (루트 경로에서 모바일 앱 노출)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("ENV", "development").lower() == "development"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=is_dev)

