"""
LLM Service - OpenAI Responses API (Standardized)
"""
import httpx
import json
from typing import Optional, Any
from app.core.config import settings
from app.core.errors import WorkflowError, ErrorCode


class LLMService:
    """
    OpenAI Responses API 서비스 (표준화)

    - 기존 chat_completion/vision_completion 인터페이스는 유지
    - 내부 구현만 /responses로 전환
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = api_base or settings.OPENAI_API_BASE
        self.model = model or settings.OPENAI_MODEL or "gpt-5"

        if not self.api_key:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API key not configured")
        if not self.api_base:
            raise WorkflowError(code=ErrorCode.INTERNAL_ERROR, message="OpenAI API base not configured")

    def _join_url(self, path: str) -> str:
        base = (self.api_base or "").rstrip("/")
        path = (path or "").lstrip("/")
        return f"{base}/{path}"

    def _extract_output_text(self, resp_json: dict) -> str:
        if not isinstance(resp_json, dict):
            return ""
        ot = resp_json.get("output_text")
        if isinstance(ot, str) and ot.strip():
            return ot.strip()

        chunks: list[str] = []
        for item in resp_json.get("output", []) or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []) or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    t = part.get("text", "")
                    if isinstance(t, str) and t:
                        chunks.append(t)
        return "\n".join(chunks).strip()

    def _map_usage_compat(self, usage: dict) -> dict:
        usage = usage or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
        # 기존 호환(prompt/completion) + 표준(input/output) 둘 다 제공
        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    async def _post_responses(self, payload: dict, timeout: float) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = self._join_url("/responses")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                detail = response.text
                try:
                    ej = response.json()
                    detail = ej.get("error", {}).get("message", detail)
                except Exception:
                    pass
                raise WorkflowError(
                    code=ErrorCode.LLM_API_ERROR,
                    message=f"OpenAI API error: {detail}",
                    details={"status_code": response.status_code, "error": detail},
                )

            return response.json()

        except httpx.TimeoutException:
            raise WorkflowError(code=ErrorCode.LLM_API_ERROR, message="OpenAI API timeout", retryable=True)
        except httpx.RequestError as e:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message=f"OpenAI API request error: {str(e)}",
                details={"error": str(e)},
                retryable=True,
            )

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        force_json: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> dict:
        if force_json and "json" not in (user_prompt or "").lower():
            user_prompt = (user_prompt or "") + "\n\nRespond in valid JSON format."

        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": system_prompt,
            "input": [{
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            }],
            "max_output_tokens": int(max_tokens),
            "temperature": float(temperature),
        }

        if force_json:
            payload["text"] = {"format": {"type": "json_object"}}

        resp_json = await self._post_responses(payload, timeout=120.0)
        content = self._extract_output_text(resp_json)
        usage = self._map_usage_compat(resp_json.get("usage", {}))

        return {"content": content, "usage": usage}

    async def vision_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        image_base64_list: list[str],
        force_json: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model: str = None
    ) -> dict:
        vision_model = model or self.model or "gpt-5"

        if not image_base64_list:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message="No images provided",
                details={"images_count": 0},
            )

        if force_json and "json" not in (user_prompt or "").lower():
            user_prompt = (user_prompt or "") + "\n\nRespond in valid JSON format."

        content_parts: list[dict[str, Any]] = [{"type": "input_text", "text": user_prompt}]

        for img in image_base64_list:
            if not isinstance(img, str):
                continue
            if not img.startswith("data:"):
                img = f"data:image/png;base64,{img}"
            content_parts.append({"type": "input_image", "image_url": img})

        payload: dict[str, Any] = {
            "model": vision_model,
            "instructions": system_prompt,
            "input": [{"role": "user", "content": content_parts}],
            "max_output_tokens": int(max_tokens),
            "temperature": float(temperature),
        }

        if force_json:
            payload["text"] = {"format": {"type": "json_object"}}

        resp_json = await self._post_responses(payload, timeout=180.0)
        content = self._extract_output_text(resp_json)
        usage = self._map_usage_compat(resp_json.get("usage", {}))

        return {"content": content, "usage": usage, "model": vision_model}
