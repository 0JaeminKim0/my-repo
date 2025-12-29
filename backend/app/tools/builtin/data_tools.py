"""
=============================================================================
데이터 처리 Tool들
=============================================================================

이 파일은 데이터 변환, 필터링, 매핑 등의 Tool들을 포함합니다.
Workflow에서 노드 간 데이터 변환에 유용합니다.

=============================================================================
"""

from app.tools.base import BaseTool, ToolParameter, ToolParameterType, WorkflowError, ErrorCode
from typing import Any
import json


class DataMapTool(BaseTool):
    """
    데이터 매핑 Tool
    
    입력 객체의 필드를 재구성하여 새로운 형태로 변환합니다.
    """
    
    tool_id = "data.map"
    version = "1.0.0"
    name = "Data Mapper"
    description = "데이터 필드를 재구성합니다"
    category = "data"
    
    input_schema = [
        ToolParameter(
            name="data",
            type=ToolParameterType.OBJECT,
            description="입력 데이터",
            required=True
        ),
        ToolParameter(
            name="mapping",
            type=ToolParameterType.OBJECT,
            description="필드 매핑 (newKey: originalPath 형식)",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.OBJECT,
            description="매핑된 데이터"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        data = inputs.get("data", {})
        mapping = inputs.get("mapping", {})
        
        result = {}
        for new_key, path in mapping.items():
            value = self._get_by_path(data, path)
            result[new_key] = value
        
        return {"result": result}
    
    def _get_by_path(self, data: Any, path: str) -> Any:
        """dot-path로 값 추출"""
        if not path:
            return data
        
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if 0 <= idx < len(value) else None
            else:
                return None
        return value


class DataFilterTool(BaseTool):
    """
    데이터 필터링 Tool
    
    배열에서 조건에 맞는 항목만 추출합니다.
    """
    
    tool_id = "data.filter"
    version = "1.0.0"
    name = "Data Filter"
    description = "배열에서 조건에 맞는 항목을 필터링합니다"
    category = "data"
    
    input_schema = [
        ToolParameter(
            name="items",
            type=ToolParameterType.ARRAY,
            description="필터링할 배열",
            required=True
        ),
        ToolParameter(
            name="field",
            type=ToolParameterType.STRING,
            description="비교할 필드 경로",
            required=True
        ),
        ToolParameter(
            name="operator",
            type=ToolParameterType.STRING,
            description="비교 연산자: 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'contains', 'exists'",
            required=False,
            default="eq"
        ),
        ToolParameter(
            name="value",
            type=ToolParameterType.STRING,
            description="비교할 값",
            required=False,
            default=None
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="filtered",
            type=ToolParameterType.ARRAY,
            description="필터링된 배열"
        ),
        ToolParameter(
            name="count",
            type=ToolParameterType.INTEGER,
            description="필터링된 항목 수"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        items = inputs.get("items", [])
        field = inputs.get("field", "")
        operator = inputs.get("operator", "eq")
        value = inputs.get("value")
        
        filtered = []
        for item in items:
            item_value = self._get_by_path(item, field)
            
            if self._compare(item_value, operator, value):
                filtered.append(item)
        
        return {"filtered": filtered, "count": len(filtered)}
    
    def _get_by_path(self, data: Any, path: str) -> Any:
        if not path:
            return data
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _compare(self, item_value: Any, operator: str, value: Any) -> bool:
        try:
            if operator == "exists":
                return item_value is not None
            elif operator == "eq":
                return item_value == value
            elif operator == "ne":
                return item_value != value
            elif operator == "gt":
                return item_value > value
            elif operator == "gte":
                return item_value >= value
            elif operator == "lt":
                return item_value < value
            elif operator == "lte":
                return item_value <= value
            elif operator == "contains":
                return value in str(item_value)
            else:
                return False
        except:
            return False


class DataMergeTool(BaseTool):
    """
    데이터 병합 Tool
    
    여러 객체를 하나로 병합합니다.
    """
    
    tool_id = "data.merge"
    version = "1.0.0"
    name = "Data Merger"
    description = "여러 객체를 하나로 병합합니다"
    category = "data"
    
    input_schema = [
        ToolParameter(
            name="objects",
            type=ToolParameterType.ARRAY,
            description="병합할 객체 배열",
            required=True
        ),
        ToolParameter(
            name="strategy",
            type=ToolParameterType.STRING,
            description="병합 전략: 'shallow' (얕은 병합) 또는 'deep' (깊은 병합)",
            required=False,
            default="shallow"
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="merged",
            type=ToolParameterType.OBJECT,
            description="병합된 객체"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        objects = inputs.get("objects", [])
        strategy = inputs.get("strategy", "shallow")
        
        if not objects:
            return {"merged": {}}
        
        if strategy == "deep":
            result = {}
            for obj in objects:
                if isinstance(obj, dict):
                    result = self._deep_merge(result, obj)
        else:
            result = {}
            for obj in objects:
                if isinstance(obj, dict):
                    result.update(obj)
        
        return {"merged": result}
    
    def _deep_merge(self, base: dict, update: dict) -> dict:
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


class DataSelectTool(BaseTool):
    """
    데이터 선택 Tool
    
    객체에서 특정 필드만 선택합니다.
    """
    
    tool_id = "data.select"
    version = "1.0.0"
    name = "Data Selector"
    description = "객체에서 특정 필드만 선택합니다"
    category = "data"
    
    input_schema = [
        ToolParameter(
            name="data",
            type=ToolParameterType.OBJECT,
            description="입력 데이터",
            required=True
        ),
        ToolParameter(
            name="fields",
            type=ToolParameterType.ARRAY,
            description="선택할 필드 목록 (dot-path 지원)",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="selected",
            type=ToolParameterType.OBJECT,
            description="선택된 필드만 포함한 객체"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        data = inputs.get("data", {})
        fields = inputs.get("fields", [])
        
        selected = {}
        for field in fields:
            value = self._get_by_path(data, field)
            if value is not None:
                # 마지막 키를 결과 키로 사용
                key = field.split(".")[-1]
                selected[key] = value
        
        return {"selected": selected}
    
    def _get_by_path(self, data: Any, path: str) -> Any:
        if not path:
            return data
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class DataTransformTool(BaseTool):
    """
    데이터 변환 Tool
    
    배열의 각 항목을 변환합니다.
    """
    
    tool_id = "data.transform"
    version = "1.0.0"
    name = "Data Transformer"
    description = "배열의 각 항목을 변환합니다"
    category = "data"
    
    input_schema = [
        ToolParameter(
            name="items",
            type=ToolParameterType.ARRAY,
            description="변환할 배열",
            required=True
        ),
        ToolParameter(
            name="mapping",
            type=ToolParameterType.OBJECT,
            description="필드 매핑 (newKey: originalPath 형식)",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="transformed",
            type=ToolParameterType.ARRAY,
            description="변환된 배열"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        items = inputs.get("items", [])
        mapping = inputs.get("mapping", {})
        
        transformed = []
        for item in items:
            new_item = {}
            for new_key, path in mapping.items():
                value = self._get_by_path(item, path)
                new_item[new_key] = value
            transformed.append(new_item)
        
        return {"transformed": transformed}
    
    def _get_by_path(self, data: Any, path: str) -> Any:
        if not path:
            return data
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


# =============================================================================
# 새로운 데이터 Tool 추가 방법
# =============================================================================
#
# 데이터 Tool은 주로 Workflow 내에서 노드 간 데이터 변환에 사용됩니다.
# LLM 호출 없이 빠르게 데이터를 처리할 수 있습니다.
#
# 예시:
#
# class DataSortTool(BaseTool):
#     tool_id = "data.sort"
#     version = "1.0.0"
#     name = "Data Sorter"
#     description = "배열을 정렬합니다"
#     category = "data"
#     
#     input_schema = [
#         ToolParameter(name="items", type=ToolParameterType.ARRAY, ...),
#         ToolParameter(name="field", type=ToolParameterType.STRING, ...),
#         ToolParameter(name="order", type=ToolParameterType.STRING, ...),
#     ]
#     
#     output_schema = [
#         ToolParameter(name="sorted", type=ToolParameterType.ARRAY, ...),
#     ]
#     
#     async def execute(self, inputs: dict, context: dict) -> dict:
#         items = inputs.get("items", [])
#         field = inputs.get("field", "")
#         order = inputs.get("order", "asc")
#         
#         sorted_items = sorted(
#             items,
#             key=lambda x: self._get_by_path(x, field),
#             reverse=(order == "desc")
#         )
#         
#         return {"sorted": sorted_items}
#
# =============================================================================
