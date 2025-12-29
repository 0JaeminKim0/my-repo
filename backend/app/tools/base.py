"""
=============================================================================
Tool Plugin Base Classes
=============================================================================

이 파일은 Tool Plugin 시스템의 핵심입니다.
관리자/개발자가 새로운 Tool을 개발할 때 이 Base 클래스를 상속받아 구현합니다.

## Tool 개발 가이드

1. BaseTool 클래스를 상속받습니다
2. 필수 속성을 정의합니다 (tool_id, version, name, description)
3. input_schema, output_schema를 정의합니다
4. execute() 메서드를 구현합니다

## 예시 코드

```python
from app.tools.base import BaseTool, ToolParameter, ToolParameterType

class MyCustomTool(BaseTool):
    tool_id = "my.custom_tool"
    version = "1.0.0"
    name = "My Custom Tool"
    description = "이 Tool은 XX를 수행합니다"
    category = "custom"
    
    input_schema = [
        ToolParameter(
            name="input_text",
            type=ToolParameterType.STRING,
            description="입력 텍스트",
            required=True
        ),
        ToolParameter(
            name="max_length",
            type=ToolParameterType.INTEGER,
            description="최대 길이",
            required=False,
            default=100
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.STRING,
            description="처리 결과"
        ),
        ToolParameter(
            name="metadata",
            type=ToolParameterType.OBJECT,
            description="메타데이터"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        # 실제 로직 구현
        input_text = inputs.get("input_text", "")
        max_length = inputs.get("max_length", 100)
        
        result = input_text[:max_length]
        
        return {
            "result": result,
            "metadata": {
                "original_length": len(input_text),
                "truncated": len(input_text) > max_length
            }
        }
```

## Tool 등록 방법

1. app/tools/builtin/ 디렉토리에 새 파일 생성
2. BaseTool 상속한 클래스 구현
3. app/tools/builtin/__init__.py에서 import 및 등록

=============================================================================
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from app.models.schemas import ToolParameter, ToolParameterType, ToolDefinition
from app.core.errors import WorkflowError, ErrorCode


class BaseTool(ABC):
    """
    Tool Plugin 기본 클래스
    
    모든 Tool은 이 클래스를 상속받아 구현합니다.
    
    Attributes:
        tool_id: 고유 Tool ID (예: "pdf.extract", "llm.summarize")
        version: 버전 문자열 (예: "1.0.0")
        name: 표시 이름
        description: Tool 설명
        category: 카테고리 (예: "file", "llm", "text", "data")
        has_prompt: LLM 프롬프트를 사용하는 Tool인지 여부
        input_schema: 입력 파라미터 정의
        output_schema: 출력 파라미터 정의
    """
    
    # =========================================
    # 필수 속성 - 반드시 오버라이드해야 함
    # =========================================
    tool_id: str = ""
    version: str = "1.0.0"
    name: str = ""
    description: str = ""
    
    # =========================================
    # 선택 속성 - 필요시 오버라이드
    # =========================================
    category: str = "general"
    has_prompt: bool = False
    
    # 입출력 스키마
    input_schema: list[ToolParameter] = []
    output_schema: list[ToolParameter] = []
    
    def get_definition(self) -> ToolDefinition:
        """Tool 정의 반환"""
        return ToolDefinition(
            tool_id=self.tool_id,
            version=self.version,
            name=self.name,
            description=self.description,
            category=self.category,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            has_prompt=self.has_prompt
        )
    
    def validate_inputs(self, inputs: dict) -> dict:
        """
        입력 검증 및 기본값 적용
        
        Args:
            inputs: 실제 입력값
            
        Returns:
            검증 및 기본값이 적용된 입력값
            
        Raises:
            WorkflowError: 필수 입력이 누락되었거나 타입이 맞지 않는 경우
        """
        validated = {}
        
        for param in self.input_schema:
            value = inputs.get(param.name)
            
            # 필수 파라미터 검증
            if value is None:
                if param.required:
                    raise WorkflowError(
                        code=ErrorCode.TOOL_INPUT_INVALID,
                        message=f"Required input '{param.name}' is missing",
                        details={"tool_id": self.tool_id, "param": param.name}
                    )
                else:
                    value = param.default
            
            # 타입 검증 (기본적인 검증만 수행)
            if value is not None:
                if not self._check_type(value, param.type):
                    raise WorkflowError(
                        code=ErrorCode.TOOL_INPUT_INVALID,
                        message=f"Input '{param.name}' has invalid type. Expected {param.type.value}",
                        details={
                            "tool_id": self.tool_id,
                            "param": param.name,
                            "expected_type": param.type.value,
                            "actual_type": type(value).__name__
                        }
                    )
            
            validated[param.name] = value
        
        return validated
    
    def _check_type(self, value: Any, expected_type: ToolParameterType) -> bool:
        """타입 검증"""
        type_map = {
            ToolParameterType.STRING: str,
            ToolParameterType.INTEGER: int,
            ToolParameterType.NUMBER: (int, float),
            ToolParameterType.BOOLEAN: bool,
            ToolParameterType.ARRAY: list,
            ToolParameterType.OBJECT: dict,
        }
        expected = type_map.get(expected_type, object)
        return isinstance(value, expected)
    
    @abstractmethod
    async def execute(self, inputs: dict, context: dict) -> dict:
        """
        Tool 실행
        
        Args:
            inputs: 검증된 입력값 (validate_inputs를 거친 값)
            context: 실행 컨텍스트
                - run_id: 현재 Run ID
                - node_id: 현재 Node ID
                - settings: 환경 설정
                
        Returns:
            출력 딕셔너리 (output_schema에 정의된 키들 포함)
            
        Raises:
            WorkflowError: 실행 중 오류 발생 시
        """
        pass
    
    async def run(self, inputs: dict, context: dict) -> dict:
        """
        Tool 실행 (입력 검증 포함)
        
        워크플로우 엔진에서 호출하는 메인 메서드입니다.
        
        Args:
            inputs: 원시 입력값
            context: 실행 컨텍스트
            
        Returns:
            출력 딕셔너리
        """
        # 1. 입력 검증 및 기본값 적용
        validated_inputs = self.validate_inputs(inputs)
        
        # 2. 실행
        output = await self.execute(validated_inputs, context)
        
        return output


class LLMTool(BaseTool):
    """
    LLM 기반 Tool 기본 클래스
    
    OpenAI Chat Completions API를 사용하는 Tool의 기본 클래스입니다.
    프롬프트 템플릿과 LLM 호출 기능을 제공합니다.
    
    ## 사용법
    
    ```python
    class MySummaryTool(LLMTool):
        tool_id = "llm.my_summary"
        version = "1.0.0"
        name = "My Summary Tool"
        description = "텍스트를 요약합니다"
        
        # LLM Tool에서는 프롬프트를 Node에서 설정하므로
        # 기본 프롬프트만 정의하면 됩니다
        default_system_prompt = "You are a helpful assistant."
        
        input_schema = [
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="요약할 텍스트",
                required=True
            )
        ]
        
        output_schema = [
            ToolParameter(
                name="summary",
                type=ToolParameterType.STRING,
                description="요약 결과"
            )
        ]
    ```
    """
    
    has_prompt: bool = True
    default_system_prompt: str = "You are a helpful assistant."
    default_temperature: float = 0.7
    default_max_tokens: int = 2000
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        """
        LLM Tool 실행
        
        Node의 prompt 설정을 사용하여 LLM을 호출합니다.
        context에서 prompt 정보와 llm_client를 가져옵니다.
        """
        from app.services.llm_service import LLMService
        
        # 프롬프트 구성
        prompt_config = context.get("prompt", {})
        system_prompt = prompt_config.get("system", self.default_system_prompt)
        user_template = prompt_config.get("user", "")
        force_json = prompt_config.get("force_json", False)
        
        # 템플릿 렌더링 ({{input.xxx}} 치환)
        user_prompt = self._render_template(user_template, inputs)
        
        # LLM 호출
        llm_service: LLMService = context.get("llm_service")
        if not llm_service:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="LLM service not available in context"
            )
        
        response = await llm_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json=force_json,
            temperature=self.default_temperature,
            max_tokens=self.default_max_tokens
        )
        
        # 토큰 사용량 기록
        context["token_usage"] = response.get("usage", {})
        
        # JSON 응답인 경우 파싱
        content = response.get("content", "")
        if force_json:
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트로 반환
                return {"result": content}
        
        return {"result": content}
    
    def _render_template(self, template: str, inputs: dict) -> str:
        """
        프롬프트 템플릿 렌더링
        
        {{input.xxx}} 형식의 플레이스홀더를 실제 값으로 치환합니다.
        """
        import re
        
        def replace_placeholder(match):
            path = match.group(1)  # input.xxx
            parts = path.split(".")
            if parts[0] == "input" and len(parts) > 1:
                key = ".".join(parts[1:])
                value = self._get_nested_value(inputs, key)
                return str(value) if value is not None else ""
            return match.group(0)
        
        return re.sub(r"\{\{([^}]+)\}\}", replace_placeholder, template)
    
    def _get_nested_value(self, data: dict, path: str) -> Any:
        """dot-path로 중첩 값 가져오기"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


# =========================================
# 편의를 위한 re-export
# =========================================
__all__ = [
    "BaseTool",
    "LLMTool", 
    "ToolParameter",
    "ToolParameterType",
    "WorkflowError",
    "ErrorCode"
]
