"""
Pydantic Schemas - API Request/Response 모델
PRD 5.1 Workflow JSON 표준 준수
"""
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# ============================================================
# Tool 관련 스키마
# ============================================================

class ToolParameterType(str, Enum):
    """Tool 파라미터 타입"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool 입력/출력 파라미터 정의"""
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None


class ToolDefinition(BaseModel):
    """
    Tool 정의 스키마
    - 관리자가 개발한 Tool의 메타데이터
    """
    tool_id: str = Field(..., description="고유 Tool ID (예: pdf.extract)")
    version: str = Field(..., description="버전 (예: 1.0.0)")
    name: str = Field(..., description="Tool 표시명")
    description: str = Field(..., description="Tool 설명")
    category: str = Field(default="general", description="카테고리")
    input_schema: list[ToolParameter] = Field(default_factory=list)
    output_schema: list[ToolParameter] = Field(default_factory=list)
    
    # LLM Tool인 경우 프롬프트 템플릿 포함
    has_prompt: bool = Field(default=False, description="LLM 프롬프트 Tool 여부")


class ToolListResponse(BaseModel):
    """Tool 목록 응답"""
    tools: list[ToolDefinition]
    total: int


# ============================================================
# Workflow 관련 스키마 (PRD 5.1)
# ============================================================

class ConstantMapping(BaseModel):
    """상수 매핑"""
    type: Literal["constant"] = "constant"
    value: Any


class FromNodeMapping(BaseModel):
    """이전 노드 출력 참조 매핑"""
    type: Literal["fromNode"] = "fromNode"
    node_id: str = Field(..., description="참조할 노드 ID")
    path: str = Field(..., description="dot-path 문법 (예: extracted_text, meta.chars)")


# Union 타입으로 매핑 정의
InputMapping = Union[ConstantMapping, FromNodeMapping]


class NodePrompt(BaseModel):
    """LLM Tool용 프롬프트 설정"""
    system: str = Field(default="You are a helpful assistant.")
    user: str = Field(..., description="사용자 프롬프트 ({{input.xxx}} 템플릿 사용)")
    force_json: bool = Field(default=False, description="JSON 응답 강제 여부")


class WorkflowNode(BaseModel):
    """
    Workflow 노드 정의 (PRD 5.1)
    - tool_id + version 고정 참조
    - input_mapping으로 데이터 전달
    """
    node_id: str = Field(..., description="노드 고유 ID")
    tool_id: str = Field(..., description="Tool ID")
    version: str = Field(..., description="Tool 버전")
    input_mapping: dict[str, InputMapping] = Field(
        default_factory=dict,
        description="입력 매핑 (constant | fromNode)"
    )
    prompt: Optional[NodePrompt] = Field(
        default=None,
        description="LLM Tool용 프롬프트"
    )


class FinalOutputMapping(BaseModel):
    """최종 출력 매핑"""
    node_id: str
    path: str


class FinalOutputSchema(BaseModel):
    """최종 출력 스키마"""
    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, dict] = Field(default_factory=dict)


class WorkflowFinalOutput(BaseModel):
    """Workflow 최종 출력 정의"""
    schema_def: FinalOutputSchema = Field(alias="schema")
    mapping: dict[str, FinalOutputMapping]
    
    class Config:
        populate_by_name = True


# ============================================================
# Workflow CRUD 스키마
# ============================================================

class WorkflowCreate(BaseModel):
    """Workflow 생성 요청"""
    project_id: str = Field(default="default")
    name: str
    description: str = ""
    nodes: list[WorkflowNode]
    final_output: Optional[WorkflowFinalOutput] = None


class WorkflowUpdate(BaseModel):
    """Workflow 수정 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list[WorkflowNode]] = None
    final_output: Optional[WorkflowFinalOutput] = None


class WorkflowResponse(BaseModel):
    """Workflow 응답"""
    workflow_id: str
    project_id: str
    name: str
    description: str
    nodes: list[WorkflowNode]
    final_output: Optional[WorkflowFinalOutput] = None
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    """Workflow 목록 응답"""
    workflows: list[WorkflowResponse]
    total: int


# ============================================================
# Run 관련 스키마 (PRD 6)
# ============================================================

class RunStatus(str, Enum):
    """Run 실행 상태"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class NodeTraceStatus(str, Enum):
    """Node 실행 상태"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NodeTraceError(BaseModel):
    """Node 실행 에러 (PRD 6.3)"""
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class NodeTrace(BaseModel):
    """
    Node 실행 트레이스 (PRD 6.3)
    - 각 Node 실행마다 기록
    """
    node_id: str
    tool_id: str
    status: NodeTraceStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    input_summary: dict = Field(default_factory=dict, description="입력 요약")
    output_summary: dict = Field(default_factory=dict, description="출력 요약")
    error: Optional[NodeTraceError] = None


class RunCost(BaseModel):
    """실행 비용 정보"""
    tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class RunMeta(BaseModel):
    """Run 메타 정보 (PRD 6.1)"""
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: RunStatus = RunStatus.PENDING
    cost: RunCost = Field(default_factory=RunCost)


class RunCreate(BaseModel):
    """Run 실행 요청 (PRD 9)"""
    workflow_id: str
    draft: Optional[dict] = Field(
        default=None,
        description="Optional: Workflow 오버라이드 (개발/테스트용)"
    )


class RunResponse(BaseModel):
    """
    Run 응답 (PRD 6.1, 9)
    - Run Context + Node Trace
    """
    run_id: str
    workflow_id: str
    status: RunStatus
    trace: list[NodeTrace] = Field(default_factory=list)
    node_outputs: dict[str, Any] = Field(default_factory=dict)
    final_output: Optional[dict] = None
    error: Optional[NodeTraceError] = None
    meta: RunMeta = Field(default_factory=RunMeta)
    created_at: datetime


class RunListResponse(BaseModel):
    """Run 목록 응답"""
    runs: list[RunResponse]
    total: int


# ============================================================
# 파일 업로드 관련
# ============================================================

class FileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    file_ref: str
    filename: str
    size: int
    content_type: str
