"""
Workflows API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.database import WorkflowModel
from app.models.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, 
    WorkflowListResponse, WorkflowNode, WorkflowFinalOutput
)
from app.core.errors import WorkflowError, ErrorCode, get_http_status

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


def _model_to_response(model: WorkflowModel) -> WorkflowResponse:
    """DB 모델을 응답 스키마로 변환"""
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


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    project_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Workflow 목록 조회
    
    Query Parameters:
        project_id: 프로젝트 ID 필터 (선택)
    """
    query = select(WorkflowModel)
    if project_id:
        query = query.where(WorkflowModel.project_id == project_id)
    query = query.order_by(WorkflowModel.created_at.desc())
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    workflows = [_model_to_response(m) for m in models]
    return WorkflowListResponse(workflows=workflows, total=len(workflows))


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    새 Workflow 생성
    """
    # 노드를 JSON으로 변환
    nodes_json = [node.model_dump() for node in data.nodes]
    
    # final_output을 JSON으로 변환
    final_output_json = None
    if data.final_output:
        final_output_json = data.final_output.model_dump(by_alias=True)
    
    model = WorkflowModel(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        nodes_json=nodes_json,
        final_output_json=final_output_json
    )
    
    db.add(model)
    await db.commit()
    await db.refresh(model)
    
    return _model_to_response(model)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 Workflow 조회
    """
    result = await db.execute(
        select(WorkflowModel).where(WorkflowModel.workflow_id == workflow_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.WORKFLOW_NOT_FOUND.value,
                    "message": f"Workflow not found: {workflow_id}",
                    "details": {"workflow_id": workflow_id},
                    "retryable": False
                }
            }
        )
    
    return _model_to_response(model)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Workflow 수정
    """
    result = await db.execute(
        select(WorkflowModel).where(WorkflowModel.workflow_id == workflow_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.WORKFLOW_NOT_FOUND.value,
                    "message": f"Workflow not found: {workflow_id}",
                    "details": {"workflow_id": workflow_id},
                    "retryable": False
                }
            }
        )
    
    # 업데이트
    if data.name is not None:
        model.name = data.name
    if data.description is not None:
        model.description = data.description
    if data.nodes is not None:
        model.nodes_json = [node.model_dump() for node in data.nodes]
    if data.final_output is not None:
        model.final_output_json = data.final_output.model_dump(by_alias=True)
    
    await db.commit()
    await db.refresh(model)
    
    return _model_to_response(model)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Workflow 삭제
    """
    result = await db.execute(
        select(WorkflowModel).where(WorkflowModel.workflow_id == workflow_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.WORKFLOW_NOT_FOUND.value,
                    "message": f"Workflow not found: {workflow_id}",
                    "details": {"workflow_id": workflow_id},
                    "retryable": False
                }
            }
        )
    
    await db.delete(model)
    await db.commit()
