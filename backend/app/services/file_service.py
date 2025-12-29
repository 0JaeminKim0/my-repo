"""
File Service - 파일 업로드 및 관리
"""
import os
import uuid
import aiofiles
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.database import FileModel


class FileService:
    """
    파일 업로드 및 관리 서비스
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = settings.UPLOAD_DIR
        
        # 업로드 디렉토리 생성
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def upload(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """
        파일 업로드
        
        Args:
            filename: 원본 파일명
            content: 파일 내용
            content_type: MIME 타입
            
        Returns:
            {
                "file_ref": str,
                "filename": str,
                "size": int,
                "content_type": str
            }
        """
        # 파일 참조 ID 생성
        file_ref = f"file_{uuid.uuid4().hex[:12]}"
        
        # 확장자 추출
        ext = os.path.splitext(filename)[1]
        
        # 저장 경로
        filepath = os.path.join(self.upload_dir, f"{file_ref}{ext}")
        
        # 파일 저장
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)
        
        # DB에 기록
        file_model = FileModel(
            file_ref=file_ref,
            filename=filename,
            filepath=filepath,
            content_type=content_type,
            size=len(content)
        )
        self.db.add(file_model)
        await self.db.commit()
        
        return {
            "file_ref": file_ref,
            "filename": filename,
            "size": len(content),
            "content_type": content_type
        }
    
    async def get_file(self, file_ref: str) -> Optional[dict]:
        """
        파일 정보 조회
        
        Args:
            file_ref: 파일 참조 ID
            
        Returns:
            파일 정보 또는 None
        """
        result = await self.db.execute(
            select(FileModel).where(FileModel.file_ref == file_ref)
        )
        file_model = result.scalar_one_or_none()
        
        if not file_model:
            return None
        
        return {
            "file_ref": file_model.file_ref,
            "filename": file_model.filename,
            "filepath": file_model.filepath,
            "content_type": file_model.content_type,
            "size": file_model.size
        }
    
    async def delete_file(self, file_ref: str) -> bool:
        """
        파일 삭제
        
        Args:
            file_ref: 파일 참조 ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self.db.execute(
            select(FileModel).where(FileModel.file_ref == file_ref)
        )
        file_model = result.scalar_one_or_none()
        
        if not file_model:
            return False
        
        # 파일 삭제
        if os.path.exists(file_model.filepath):
            os.remove(file_model.filepath)
        
        # DB에서 삭제
        await self.db.delete(file_model)
        await self.db.commit()
        
        return True
