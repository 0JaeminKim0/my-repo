"""
Runs API Endpoints (PRD 9)
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.database import WorkflowModel, RunModel, NodeTraceModel
from app.models.schemas import (
    RunCreate, RunResponse, RunListResponse,
    RunStatus, NodeTraceStatus, NodeTrace, NodeTraceError,
    RunMeta, RunCost, WorkflowResponse, WorkflowNode, WorkflowFinalOutput
)
from app.services.workflow_engine import WorkflowEngine
from app.core.errors import ErrorCode

router = APIRouter(prefix="/api/runs", tags=["Runs"])


def _model_to_response(model: RunModel, traces: list = None) -> RunResponse:
    """DB 모델을 응답 스키마로 변환"""
    # Node Traces 변환
    trace_list = []
    if traces:
        for t in traces:
            trace_list.append(NodeTrace(
                node_id=t.node_id,
                tool_id=t.tool_id,
                status=t.status,
                started_at=t.started_at,
                ended_at=t.ended_at,
                input_summary=t.input_summary_json or {},
                output_summary=t.output_summary_json or {},
                error=NodeTraceError(**t.error_json) if t.error_json else None
            ))
    
    # Error 변환
    error = None
    if model.error_json:
        error = NodeTraceError(**model.error_json)
    
    return RunResponse(
        run_id=model.run_id,
        workflow_id=model.workflow_id,
        status=model.status,
        trace=trace_list,
        node_outputs=model.node_outputs_json or {},
        final_output=model.final_output_json,
        error=error,
        meta=RunMeta(
            started_at=model.started_at,
            ended_at=model.ended_at,
            status=model.status,
            cost=RunCost(
                tokens=model.total_tokens,
                prompt_tokens=model.prompt_tokens,
                completion_tokens=model.completion_tokens
            )
        ),
        created_at=model.created_at
    )


def _workflow_model_to_response(model: WorkflowModel) -> WorkflowResponse:
    """Workflow DB 모델을 응답 스키마로 변환"""
    nodes = []
    for node_data in model.nodes_json or []:
        nodes.append(WorkflowNode(**node_data))
    
    final_output = None
    if model.final_output_json:
        final_output = WorkflowFinalOutput(**model.final_output_json)
    
    return WorkflowResponse(
        workflow_id=model.workflow_id,
        project_id=model.project_id,
        name=model.name,
        description=model.description,
        nodes=nodes,
        final_output=final_output,
        created_at=model.created_at,
        updated_at=model.updated_at
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    workflow_id: str = None,
    status: RunStatus = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Run 목록 조회
    
    Query Parameters:
        workflow_id: Workflow ID 필터 (선택)
        status: 상태 필터 (선택)
        limit: 최대 개수 (기본값: 50)
    """
    query = select(RunModel)
    
    if workflow_id:
        query = query.where(RunModel.workflow_id == workflow_id)
    if status:
        query = query.where(RunModel.status == status)
    
    query = query.order_by(RunModel.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    runs = [_model_to_response(m) for m in models]
    return RunListResponse(runs=runs, total=len(runs))


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    data: RunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    새 Run 실행 (PRD 9)
    
    Request Body:
        workflow_id: 실행할 Workflow ID
        draft: 선택적 오버라이드 (테스트용)
    """
    # Workflow 조회
    result = await db.execute(
        select(WorkflowModel).where(WorkflowModel.workflow_id == data.workflow_id)
    )
    workflow_model = result.scalar_one_or_none()
    
    if not workflow_model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.WORKFLOW_NOT_FOUND.value,
                    "message": f"Workflow not found: {data.workflow_id}",
                    "details": {"workflow_id": data.workflow_id},
                    "retryable": False
                }
            }
        )
    
    # Run 생성
    run_model = RunModel(
        workflow_id=data.workflow_id,
        status=RunStatus.PENDING
    )
    db.add(run_model)
    await db.commit()
    await db.refresh(run_model)
    
    # Workflow 실행 (동기 실행 - MVP에서는 간단하게)
    workflow = _workflow_model_to_response(workflow_model)
    engine = WorkflowEngine(db)
    
    result = await engine.execute(
        run_id=run_model.run_id,
        workflow=workflow,
        draft_override=data.draft
    )
    
    # 결과 조회
    await db.refresh(run_model)
    
    # Trace 조회
    traces_result = await db.execute(
        select(NodeTraceModel)
        .where(NodeTraceModel.run_id == run_model.run_id)
        .order_by(NodeTraceModel.started_at)
    )
    traces = traces_result.scalars().all()
    
    return _model_to_response(run_model, traces)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 Run 조회 (PRD 9)
    """
    # Run 조회
    result = await db.execute(
        select(RunModel).where(RunModel.run_id == run_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.RUN_NOT_FOUND.value,
                    "message": f"Run not found: {run_id}",
                    "details": {"run_id": run_id},
                    "retryable": False
                }
            }
        )
    
    # Trace 조회
    traces_result = await db.execute(
        select(NodeTraceModel)
        .where(NodeTraceModel.run_id == run_id)
        .order_by(NodeTraceModel.started_at)
    )
    traces = traces_result.scalars().all()
    
    return _model_to_response(model, traces)


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Run 삭제
    """
    result = await db.execute(
        select(RunModel).where(RunModel.run_id == run_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.RUN_NOT_FOUND.value,
                    "message": f"Run not found: {run_id}",
                    "details": {"run_id": run_id},
                    "retryable": False
                }
            }
        )
    
    await db.delete(model)
    await db.commit()
