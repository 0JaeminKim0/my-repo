"""
SQLAlchemy Database Models
- Workflow, Run, NodeTrace 등 영속화
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.schemas import RunStatus, NodeTraceStatus
import uuid


def generate_id(prefix: str = "") -> str:
    """고유 ID 생성"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class WorkflowModel(Base):
    """Workflow 테이블"""
    __tablename__ = "workflows"
    
    workflow_id = Column(String(50), primary_key=True, default=lambda: generate_id("wf_"))
    project_id = Column(String(50), default="default", index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    
    # JSON으로 nodes와 final_output 저장
    nodes_json = Column(JSON, nullable=False)
    final_output_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    runs = relationship("RunModel", back_populates="workflow", cascade="all, delete-orphan")


class RunModel(Base):
    """Run 테이블"""
    __tablename__ = "runs"
    
    run_id = Column(String(50), primary_key=True, default=lambda: generate_id("run_"))
    workflow_id = Column(String(50), ForeignKey("workflows.workflow_id"), nullable=False, index=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING)
    
    # JSON으로 node_outputs, final_output, error 저장
    node_outputs_json = Column(JSON, default=dict)
    final_output_json = Column(JSON, nullable=True)
    error_json = Column(JSON, nullable=True)
    
    # 메타 정보
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("WorkflowModel", back_populates="runs")
    traces = relationship("NodeTraceModel", back_populates="run", cascade="all, delete-orphan")


class NodeTraceModel(Base):
    """Node Trace 테이블 (PRD 6.3)"""
    __tablename__ = "node_traces"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey("runs.run_id"), nullable=False, index=True)
    node_id = Column(String(50), nullable=False)
    tool_id = Column(String(100), nullable=False)
    status = Column(SQLEnum(NodeTraceStatus), default=NodeTraceStatus.PENDING)
    
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # JSON으로 input/output 요약, 에러 저장
    input_summary_json = Column(JSON, default=dict)
    output_summary_json = Column(JSON, default=dict)
    error_json = Column(JSON, nullable=True)
    
    # Relationships
    run = relationship("RunModel", back_populates="traces")


class FileModel(Base):
    """업로드 파일 테이블"""
    __tablename__ = "files"
    
    file_ref = Column(String(50), primary_key=True, default=lambda: generate_id("file_"))
    filename = Column(String(500), nullable=False)
    filepath = Column(String(1000), nullable=False)
    content_type = Column(String(100), default="application/octet-stream")
    size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
