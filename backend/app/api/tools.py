"""
Tools API Endpoints
"""
from fastapi import APIRouter, HTTPException
from app.tools.registry import tool_registry
from app.models.schemas import ToolListResponse, ToolDefinition
from app.core.errors import WorkflowError, get_http_status

router = APIRouter(prefix="/api/tools", tags=["Tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools(category: str = None):
    """
    모든 Tool 목록 조회
    
    Query Parameters:
        category: 카테고리 필터 (선택)
    """
    if category:
        tools = tool_registry.list_by_category(category)
    else:
        tools = tool_registry.list_all()
    
    return ToolListResponse(tools=tools, total=len(tools))


@router.get("/categories")
async def list_categories():
    """
    모든 Tool 카테고리 목록 조회
    """
    categories = tool_registry.get_categories()
    return {"categories": categories}


@router.get("/{tool_id}", response_model=ToolDefinition)
async def get_tool(tool_id: str, version: str = None):
    """
    특정 Tool 조회
    
    Path Parameters:
        tool_id: Tool ID
        
    Query Parameters:
        version: Tool 버전 (선택, 기본값: 최신)
    """
    try:
        tool = tool_registry.get(tool_id, version)
        return tool.get_definition()
    except WorkflowError as e:
        raise HTTPException(
            status_code=get_http_status(e.code),
            detail=e.to_standard_error().model_dump()
        )
