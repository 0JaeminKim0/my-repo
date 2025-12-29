"""
=============================================================================
LLM 기반 Tool들 (Responses API 표준화 버전)
=============================================================================

변경 요약
1) SummarizeTool/TranslateTool/ExtractInfoTool/AnalyzeTool/GenerateTool:
   - 기존 LLMTool(Chat Completions 전용) 의존을 제거하고
   - ResponsesLLMTool(Responses API 전용 베이스)로 전환

2) VisionExtractTool:
   - /chat/completions -> /responses
   - messages+image_url/text -> instructions + input + (input_text/input_image)
   - response_format -> text.format(json_object)
   - output_text / output[] 기반 파싱
   - usage: input_tokens/output_tokens/total_tokens

주의
- 이 파일만 바꿔도 동작하게 하려면, llm_service 의존을 제거하고
  여기서 직접 httpx로 호출하도록 구성했습니다.
- 만약 조직 표준이 llm_service 경유라면, 별도로 llm_service 자체를 Responses로 표준화해야 합니다.
=============================================================================
"""

from typing import Any, Optional
import json
import httpx

from app.tools.base import BaseTool, ToolParameter, ToolParameterType, WorkflowError, ErrorCode


# =============================================================================
# Responses API 공통 헬퍼 / 베이스
# =============================================================================

def _join_url(base: str, path: str) -> str:
    base = (base or "").rstrip("/")
    path = (path or "").lstrip("/")
    return f"{base}/{path}"


def _extract_responses_output_text(resp_json: dict) -> str:
    """
    Responses API 응답에서 텍스트를 안전하게 추출
    - output_text가 있으면 우선 사용
    - 없으면 output[] -> message -> content[]의 output_text를 조립
    """
    if not isinstance(resp_json, dict):
        return ""

    ot = resp_json.get("output_text")
    if isinstance(ot, str) and ot.strip():
        return ot.strip()

    chunks: list[str] = []
    for item in resp_json.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                t = part.get("text", "")
                if isinstance(t, str) and t:
                    chunks.append(t)

    return "\n".join(chunks).strip()


class ResponsesLLMTool(BaseTool):
    """
    Responses API 기반 LLM Tool 베이스 클래스

    Node prompt 설정 사용:
      - system: 시스템 프롬프트
      - user: 사용자 프롬프트 ({{input.xxx}} 템플릿)
      - force_json: JSON 응답 강제

    Context에서 settings를 사용합니다:
      - app.core.config.settings.OPENAI_API_KEY
      - app.core.config.settings.OPENAI_API_BASE

    선택적으로 prompt_config에 model을 넣을 수 있습니다:
      - context["prompt"]["model"]  (예: "gpt-5")
    """

    has_prompt: bool = True

    default_model: str = "gpt-5"
    default_system_prompt: str = "You are a helpful assistant."
    default_temperature: float = 0.7
    default_max_output_tokens: int = 2000

    async def execute(self, inputs: dict, context: dict) -> dict:
        from app.core.config import settings

        prompt_config = context.get("prompt", {})
        system_prompt = prompt_config.get("system", self.default_system_prompt)
        user_template = prompt_config.get("user", "")
        force_json = bool(prompt_config.get("force_json", False))

        # 모델 선택 (Node에서 override 가능)
        model = prompt_config.get("model", getattr(self, "default_model", "gpt-5"))

        user_prompt = self._render_template(user_template, inputs)

        api_key = settings.OPENAI_API_KEY
        api_base = settings.OPENAI_API_BASE
        if not api_key:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API key not configured")
        if not api_base:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API base not configured")

        payload: dict[str, Any] = {
            "model": model,
            "instructions": system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_prompt}
                    ],
                }
            ],
            "max_output_tokens": int(getattr(self, "default_max_output_tokens", self.default_max_output_tokens)),
            # temperature는 Responses에서도 지원되는 경우가 있으나,
            # 게이트웨이/SDK 호환성을 위해 선택적으로만 넣습니다.
            "temperature": float(getattr(self, "default_temperature", self.default_temperature)),
        }

        if force_json:
            payload["text"] = {"format": {"type": "json_object"}}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = _join_url(api_base, "/responses")

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            detail = resp.text
            try:
                ej = resp.json()
                detail = ej.get("error", {}).get("message", detail)
            except Exception:
                pass
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message=f"OpenAI API error: {detail}",
                details={"status_code": resp.status_code, "model": model},
            )

        resp_json = resp.json()

        # usage 기록 (Responses 포맷)
        usage = resp_json.get("usage", {}) or {}
        context["token_usage"] = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

        raw_text = _extract_responses_output_text(resp_json)

        if force_json:
            try:
                parsed = json.loads(raw_text) if raw_text else {}
                # JSON 강제인 경우, Tool의 output_schema에 맞춰 result로 감싸는 게 안전
                return {"result": parsed}
            except json.JSONDecodeError:
                return {"result": {"raw_response": raw_text}}

        return {"result": raw_text}

    # -------------------------
    # 템플릿 렌더러 (base.py와 동일 로직)
    # -------------------------
    def _render_template(self, template: str, inputs: dict) -> str:
        import re

        def replace_placeholder(match):
            path = match.group(1)
            parts = path.split(".")
            if parts[0] == "input" and len(parts) > 1:
                key = ".".join(parts[1:])
                value = self._get_nested_value(inputs, key)
                return str(value) if value is not None else ""
            return match.group(0)

        return re.sub(r"\{\{([^}]+)\}\}", replace_placeholder, template)

    def _get_nested_value(self, data: dict, path: str) -> Any:
        keys = path.split(".")
        value: Any = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


# =============================================================================
# Text LLM Tools (ResponsesLLMTool로 전환)
# =============================================================================

class SummarizeTool(ResponsesLLMTool):
    tool_id = "llm.summarize"
    version = "1.0.0"
    name = "Text Summarizer"
    description = "LLM을 사용하여 텍스트를 요약합니다"
    category = "llm"

    default_system_prompt = "You are a professional text summarizer. Provide clear and concise summaries."
    default_max_output_tokens = 10000

    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="요약할 텍스트",
            required=True
        )
    ]

    output_schema = [
        ToolParameter(name="summary", type=ToolParameterType.STRING, description="요약 결과"),
        ToolParameter(name="result", type=ToolParameterType.STRING, description="요약 결과 (대체 키)"),
    ]


class TranslateTool(ResponsesLLMTool):
    tool_id = "llm.translate"
    version = "1.0.0"
    name = "Text Translator"
    description = "LLM을 사용하여 텍스트를 번역합니다"
    category = "llm"

    default_system_prompt = "You are a professional translator. Translate accurately while maintaining the original meaning and tone."
    default_temperature = 0.3
    default_max_output_tokens = 2000

    input_schema = [
        ToolParameter(name="text", type=ToolParameterType.STRING, description="번역할 텍스트", required=True),
        ToolParameter(
            name="target_language",
            type=ToolParameterType.STRING,
            description="대상 언어 (예: Korean, English, Japanese)",
            required=False,
            default="English",
        ),
    ]

    output_schema = [
        ToolParameter(name="translated", type=ToolParameterType.STRING, description="번역 결과"),
        ToolParameter(name="result", type=ToolParameterType.STRING, description="번역 결과 (대체 키)"),
    ]


class ExtractInfoTool(ResponsesLLMTool):
    tool_id = "llm.extract"
    version = "1.0.0"
    name = "Information Extractor"
    description = "LLM을 사용하여 텍스트에서 구조화된 정보를 추출합니다"
    category = "llm"

    default_system_prompt = "You extract structured information from text."
    default_temperature = 0.2
    default_max_output_tokens = 1000

    input_schema = [
        ToolParameter(name="text", type=ToolParameterType.STRING, description="정보를 추출할 텍스트", required=True)
    ]

    output_schema = [
        ToolParameter(name="result", type=ToolParameterType.OBJECT, description="추출된 정보 (JSON)")
    ]


class AnalyzeTool(ResponsesLLMTool):
    tool_id = "llm.analyze"
    version = "1.0.0"
    name = "Text Analyzer"
    description = "LLM을 사용하여 데이터를 분석합니다"
    category = "llm"

    default_system_prompt = "You are an expert text analyst. Provide thorough and insightful analysis."
    default_temperature = 0.5
    default_max_output_tokens = 1500

    input_schema = [
        ToolParameter(name="text", type=ToolParameterType.STRING, description="분석할 텍스트", required=True)
    ]

    output_schema = [
        ToolParameter(name="analysis", type=ToolParameterType.STRING, description="분석 결과"),
        ToolParameter(name="result", type=ToolParameterType.OBJECT, description="분석 결과 (JSON, force_json=true인 경우)"),
    ]


class GenerateTool(ResponsesLLMTool):
    tool_id = "llm.generate"
    version = "1.0.0"
    name = "Text Generator"
    description = "LLM을 사용하여 텍스트를 생성합니다"
    category = "llm"

    default_system_prompt = "You are a professional content writer. Generate high-quality content based on the given instructions."
    default_temperature = 0.7
    default_max_output_tokens = 2000

    input_schema = [
        ToolParameter(name="prompt", type=ToolParameterType.STRING, description="생성 지시사항 또는 주제", required=True),
        ToolParameter(name="context", type=ToolParameterType.STRING, description="추가 컨텍스트 (선택)", required=False, default=""),
    ]

    output_schema = [
        ToolParameter(name="generated", type=ToolParameterType.STRING, description="생성된 텍스트"),
        ToolParameter(name="result", type=ToolParameterType.STRING, description="생성된 텍스트 (대체 키)"),
    ]


# =============================================================================
# VisionExtractTool (Responses API로 전환)
# =============================================================================

class VisionExtractTool(BaseTool):
    """
    Vision Extract Tool (Responses API 기반)

    Input:
        - images: base64 이미지 배열
        - prompt: 추출/분석 지시사항
        - output_format: "text" | "json"
        - model: 기본 gpt-5
    """

    tool_id = "llm.vision_extract"
    version = "1.0.0"
    name = "Vision Extractor (GPT-5)"
    description = "이미지에서 GPT-5로 정보를 추출합니다. 표, 차트, 손글씨 인식 가능."
    category = "llm"
    has_prompt = False

    input_schema = [
        ToolParameter(
            name="images",
            type=ToolParameterType.ARRAY,
            description="base64 인코딩된 이미지 배열 (pdf.to_images 출력과 연결)",
            required=True
        ),
        ToolParameter(
            name="prompt",
            type=ToolParameterType.STRING,
            description="추출/분석 지시사항 (예: '이 이미지에서 텍스트를 모두 추출해줘')",
            required=True
        ),
        ToolParameter(
            name="output_format",
            type=ToolParameterType.STRING,
            description="출력 형식: 'text' 또는 'json' (기본값: 'json')",
            required=False,
            default="json"
        ),
        ToolParameter(
            name="model",
            type=ToolParameterType.STRING,
            description="사용할 모델 (기본값: 'gpt-5')",
            required=False,
            default="gpt-5"
        )
    ]

    output_schema = [
        ToolParameter(name="result", type=ToolParameterType.OBJECT, description="분석 결과 (json이면 object, text면 string)"),
        ToolParameter(name="raw_text", type=ToolParameterType.STRING, description="원본 텍스트 응답"),
    ]

    async def execute(self, inputs: dict, context: dict) -> dict:
        from app.core.config import settings

        images = inputs.get("images", [])
        prompt = inputs.get("prompt", "")
        output_format = inputs.get("output_format", "json")
        model = inputs.get("model", "gpt-5")

        if not images:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message="No images provided",
                details={"images_count": 0}
            )
        if not prompt:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message="Prompt is required",
                details={}
            )

        api_key = settings.OPENAI_API_KEY
        api_base = settings.OPENAI_API_BASE
        if not api_key:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API key not configured")
        if not api_base:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API base not configured")

        system_prompt = (
            "You are an expert document and image analyzer. "
            "Analyze the provided images and extract information as requested. "
            "Be thorough and accurate. If you can't find certain information, explicitly state that."
        )

        # Responses 멀티모달 content 구성
        content: list[dict] = [{"type": "input_text", "text": prompt}]
        for img_base64 in images:
            # data URL 형태로 정규화
            if isinstance(img_base64, str) and not img_base64.startswith("data:"):
                img_base64 = f"data:image/png;base64,{img_base64}"
            content.append({"type": "input_image", "image_url": img_base64})

        payload: dict[str, Any] = {
            "model": model,
            "instructions": system_prompt,
            "input": [{"role": "user", "content": content}],
            "max_output_tokens": 16000,
        }

        if output_format == "json":
            payload["text"] = {"format": {"type": "json_object"}}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = _join_url(api_base, "/responses")

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code != 200:
                detail = resp.text
                try:
                    ej = resp.json()
                    detail = ej.get("error", {}).get("message", detail)
                except Exception:
                    pass
                raise WorkflowError(
                    code=ErrorCode.LLM_API_ERROR,
                    message=f"OpenAI Vision API error: {detail}",
                    details={"status_code": resp.status_code, "model": model},
                )

            resp_json = resp.json()

            # usage 기록 (Responses 포맷)
            usage = resp_json.get("usage", {}) or {}
            context["token_usage"] = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

            raw_text = _extract_responses_output_text(resp_json)

            if output_format == "json":
                try:
                    parsed = json.loads(raw_text) if raw_text else {}
                except json.JSONDecodeError:
                    parsed = {"raw_response": raw_text}
                return {"result": parsed, "raw_text": raw_text}

            return {"result": raw_text, "raw_text": raw_text}

        except httpx.TimeoutException:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message="OpenAI Vision API timeout",
                retryable=True
            )
        except httpx.RequestError as e:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message=f"OpenAI Vision API request error: {str(e)}",
                details={"error": str(e)},
                retryable=True
            )
