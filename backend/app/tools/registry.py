"""
=============================================================================
Tool Registry - Tool 등록 및 관리
=============================================================================

이 파일은 모든 Tool을 등록하고 관리하는 중앙 레지스트리입니다.

## Tool 등록 방법

### 방법 1: builtin/__init__.py에서 자동 등록 (권장)

1. app/tools/builtin/ 디렉토리에 새 Tool 파일 생성
2. app/tools/builtin/__init__.py에서 Tool 클래스 import
3. BUILTIN_TOOLS 리스트에 추가

### 방법 2: 수동 등록

```python
from app.tools.registry import tool_registry
from my_tools import MyCustomTool

# 애플리케이션 시작 시 등록
tool_registry.register(MyCustomTool())
```

### 방법 3: 데코레이터 사용 (간편)

```python
from app.tools.registry import register_tool
from app.tools.base import BaseTool

@register_tool
class MyCustomTool(BaseTool):
    tool_id = "my.custom"
    ...
```

=============================================================================
"""

from typing import Optional
from app.tools.base import BaseTool
from app.models.schemas import ToolDefinition
from app.core.errors import WorkflowError, ErrorCode


class ToolRegistry:
    """
    Tool 레지스트리
    
    모든 등록된 Tool을 관리하고 조회하는 싱글톤 클래스입니다.
    """
    
    def __init__(self):
        # tool_id -> Tool 인스턴스 매핑
        self._tools: dict[str, BaseTool] = {}
        # tool_id -> version -> Tool 인스턴스 (버전별 관리)
        self._versioned_tools: dict[str, dict[str, BaseTool]] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Tool 등록
        
        Args:
            tool: BaseTool 인스턴스
            
        Raises:
            ValueError: tool_id가 비어있는 경우
        """
        if not tool.tool_id:
            raise ValueError(f"Tool must have a tool_id: {tool.__class__.__name__}")
        
        # 최신 버전으로 등록
        self._tools[tool.tool_id] = tool
        
        # 버전별로도 등록
        if tool.tool_id not in self._versioned_tools:
            self._versioned_tools[tool.tool_id] = {}
        self._versioned_tools[tool.tool_id][tool.version] = tool
        
        print(f"✅ Tool registered: {tool.tool_id} v{tool.version}")
    
    def get(self, tool_id: str, version: Optional[str] = None) -> BaseTool:
        """
        Tool 조회
        
        Args:
            tool_id: Tool ID
            version: 버전 (None이면 최신 버전)
            
        Returns:
            Tool 인스턴스
            
        Raises:
            WorkflowError: Tool을 찾을 수 없는 경우
        """
        if version:
            # 특정 버전 조회
            versions = self._versioned_tools.get(tool_id, {})
            tool = versions.get(version)
            if not tool:
                raise WorkflowError(
                    code=ErrorCode.TOOL_NOT_FOUND,
                    message=f"Tool not found: {tool_id} v{version}",
                    details={"tool_id": tool_id, "version": version}
                )
            return tool
        else:
            # 최신 버전 조회
            tool = self._tools.get(tool_id)
            if not tool:
                raise WorkflowError(
                    code=ErrorCode.TOOL_NOT_FOUND,
                    message=f"Tool not found: {tool_id}",
                    details={"tool_id": tool_id}
                )
            return tool
    
    def list_all(self) -> list[ToolDefinition]:
        """
        모든 Tool 목록 반환
        
        Returns:
            ToolDefinition 목록
        """
        return [tool.get_definition() for tool in self._tools.values()]
    
    def list_by_category(self, category: str) -> list[ToolDefinition]:
        """
        카테고리별 Tool 목록 반환
        
        Args:
            category: 카테고리명
            
        Returns:
            해당 카테고리의 ToolDefinition 목록
        """
        return [
            tool.get_definition() 
            for tool in self._tools.values() 
            if tool.category == category
        ]
    
    def get_categories(self) -> list[str]:
        """
        모든 카테고리 목록 반환
        
        Returns:
            카테고리명 목록
        """
        return list(set(tool.category for tool in self._tools.values()))
    
    def exists(self, tool_id: str, version: Optional[str] = None) -> bool:
        """
        Tool 존재 여부 확인
        
        Args:
            tool_id: Tool ID
            version: 버전 (None이면 최신 버전)
            
        Returns:
            존재 여부
        """
        try:
            self.get(tool_id, version)
            return True
        except WorkflowError:
            return False
    
    def clear(self) -> None:
        """모든 Tool 등록 해제 (테스트용)"""
        self._tools.clear()
        self._versioned_tools.clear()


# 싱글톤 인스턴스
tool_registry = ToolRegistry()


def register_tool(cls):
    """
    Tool 등록 데코레이터
    
    클래스 정의 시 자동으로 레지스트리에 등록합니다.
    
    Usage:
        @register_tool
        class MyTool(BaseTool):
            tool_id = "my.tool"
            ...
    """
    if issubclass(cls, BaseTool):
        tool_registry.register(cls())
    return cls


def init_builtin_tools():
    """
    빌트인 Tool 초기화
    
    애플리케이션 시작 시 호출하여 모든 빌트인 Tool을 등록합니다.
    """
    # builtin 패키지에서 Tool들을 import하면 자동 등록됨
    from app.tools import builtin
    
    # builtin 모듈의 BUILTIN_TOOLS에서 직접 등록
    for tool in builtin.BUILTIN_TOOLS:
        if not tool_registry.exists(tool.tool_id, tool.version):
            tool_registry.register(tool)
    
    print(f"📦 Total {len(tool_registry._tools)} tools registered")
