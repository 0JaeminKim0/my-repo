"""
표준 에러 정의 및 처리
- PRD 7.2 표준 에러 포맷 준수
- HTTP Status 매핑 (7.3)
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """표준 에러 코드"""
    # 400 - Bad Request
    INPUT_INVALID = "INPUT_INVALID"
    TOOL_INPUT_INVALID = "TOOL_INPUT_INVALID"
    WORKFLOW_INVALID = "WORKFLOW_INVALID"
    MAPPING_INVALID = "MAPPING_INVALID"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    
    # 403 - Forbidden
    POLICY_BLOCKED = "POLICY_BLOCKED"
    
    # 404 - Not Found
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    
    # 500 - Internal Server Error
    EXECUTION_FAILED = "EXECUTION_FAILED"
    LLM_API_ERROR = "LLM_API_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class StandardError(BaseModel):
    """
    PRD 7.2 표준 에러 포맷
    {
      "error": {
        "code": "TOOL_INPUT_INVALID",
        "message": "Human readable message",
        "details": {},
        "retryable": false
      }
    }
    """
    code: ErrorCode
    message: str
    details: dict[str, Any] = {}
    retryable: bool = False


class WorkflowError(Exception):
    """Workflow 실행 관련 에러"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] = None,
        retryable: bool = False
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)
    
    def to_standard_error(self) -> StandardError:
        return StandardError(
            code=self.code,
            message=self.message,
            details=self.details,
            retryable=self.retryable
        )


# HTTP Status 매핑 (PRD 7.3)
ERROR_STATUS_MAP = {
    ErrorCode.INPUT_INVALID: 400,
    ErrorCode.TOOL_INPUT_INVALID: 400,
    ErrorCode.WORKFLOW_INVALID: 400,
    ErrorCode.MAPPING_INVALID: 400,
    ErrorCode.PATH_NOT_FOUND: 400,
    ErrorCode.POLICY_BLOCKED: 403,
    ErrorCode.TOOL_NOT_FOUND: 404,
    ErrorCode.WORKFLOW_NOT_FOUND: 404,
    ErrorCode.RUN_NOT_FOUND: 404,
    ErrorCode.NODE_NOT_FOUND: 404,
    ErrorCode.EXECUTION_FAILED: 500,
    ErrorCode.LLM_API_ERROR: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


def get_http_status(code: ErrorCode) -> int:
    """에러 코드에 대응하는 HTTP Status 반환"""
    return ERROR_STATUS_MAP.get(code, 500)
