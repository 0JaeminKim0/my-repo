"""
Files API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import FileUploadResponse
from app.services.file_service import FileService
from app.core.errors import ErrorCode

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    파일 업로드
    
    지원 파일 형식: PDF, TXT, JSON, CSV 등
    최대 크기: 10MB
    """
    # 파일 크기 검증
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.INPUT_INVALID.value,
                    "message": f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB",
                    "details": {"size": len(content), "max_size": settings.MAX_UPLOAD_SIZE},
                    "retryable": False
                }
            }
        )
    
    # 파일 저장
    file_service = FileService(db)
    result = await file_service.upload(
        filename=file.filename,
        content=content,
        content_type=file.content_type
    )
    
    return FileUploadResponse(**result)


@router.get("/{file_ref}")
async def get_file_info(
    file_ref: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파일 정보 조회
    """
    file_service = FileService(db)
    info = await file_service.get_file(file_ref)
    
    if not info:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.TOOL_INPUT_INVALID.value,
                    "message": f"File not found: {file_ref}",
                    "details": {"file_ref": file_ref},
                    "retryable": False
                }
            }
        )
    
    return {
        "file_ref": info["file_ref"],
        "filename": info["filename"],
        "content_type": info["content_type"],
        "size": info["size"]
    }


@router.delete("/{file_ref}", status_code=204)
async def delete_file(
    file_ref: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파일 삭제
    """
    file_service = FileService(db)
    deleted = await file_service.delete_file(file_ref)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.TOOL_INPUT_INVALID.value,
                    "message": f"File not found: {file_ref}",
                    "details": {"file_ref": file_ref},
                    "retryable": False
                }
            }
        )
