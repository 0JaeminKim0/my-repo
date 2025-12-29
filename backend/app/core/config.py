"""
Application Configuration
- 환경변수 기반 설정 관리
- Railway 배포 시 환경변수로 오버라이드 가능
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


def get_database_url() -> str:
    """
    Railway Volume 지원을 위한 DB 경로 결정
    - DATA_DIR 환경변수가 있으면 해당 경로 사용 (Railway Volume)
    - 없으면 기본 로컬 경로 사용
    """
    data_dir = os.environ.get("DATA_DIR", ".")
    return f"sqlite+aiosqlite:///{data_dir}/workflow_platform.db"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Workflow Tool Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database - Railway Volume 지원
    # Railway에서 DATA_DIR=/app/data 로 설정하면 Volume에 저장됨
    DATABASE_URL: str = get_database_url()
    
    # Data Directory (Railway Volume mount path)
    DATA_DIR: str = "."
    
    # OpenAI API (Gateway 경유)
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-5"
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # File Storage - Railway Volume 지원
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # DATA_DIR이 설정되면 UPLOAD_DIR도 그 안에 생성
        if self.DATA_DIR != ".":
            self.UPLOAD_DIR = f"{self.DATA_DIR}/uploads"
            self.DATABASE_URL = f"sqlite+aiosqlite:///{self.DATA_DIR}/workflow_platform.db"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
