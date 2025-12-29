"""
=============================================================================
Workflow Tool Platform - Main Application
=============================================================================

FastAPI 메인 애플리케이션

Railway 배포를 위한 단일 서비스 구조:
- FastAPI 백엔드 API
- React SPA 정적 파일 서빙

=============================================================================
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_db
from app.core.errors import WorkflowError, get_http_status
from app.tools.registry import init_builtin_tools

# API Routers
from app.api import tools, workflows, runs, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # Startup
    print("🚀 Starting Workflow Tool Platform...")
    
    # DB 초기화
    await init_db()
    print("✅ Database initialized")
    
    # Tool 등록
    init_builtin_tools()
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Workflow-enabled Tool Platform - LLM 기반 업무 자동화 플랫폼",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 글로벌 에러 핸들러
@app.exception_handler(WorkflowError)
async def workflow_error_handler(request: Request, exc: WorkflowError):
    """WorkflowError 표준 응답"""
    return JSONResponse(
        status_code=get_http_status(exc.code),
        content={"error": exc.to_standard_error().model_dump()}
    )


# API 라우터 등록
app.include_router(tools.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(files.router)


# Health Check
@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# 정적 파일 서빙 (React SPA)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# SPA Fallback (모든 경로를 index.html로)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """React SPA 서빙"""
    # API 경로는 제외
    if full_path.startswith("api/"):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "API endpoint not found"}}
        )
    
    # 정적 파일 확인
    static_file = os.path.join(static_dir, full_path)
    if os.path.isfile(static_file):
        return FileResponse(static_file)
    
    # index.html 반환 (SPA)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    # 개발 모드에서 static 폴더가 없을 때
    return JSONResponse(
        status_code=200,
        content={
            "message": "Workflow Tool Platform API",
            "version": settings.APP_VERSION,
            "docs": "/docs"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 3000)),
        reload=settings.DEBUG
    )
