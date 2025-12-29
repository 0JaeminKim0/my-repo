"""
LLM Service - OpenAI Chat Completions API
"""
import httpx
import json
from typing import Optional
from app.core.config import settings
from app.core.errors import WorkflowError, ErrorCode


class LLMService:
    """
    OpenAI Chat Completions API 서비스
    
    Gateway 경유하여 OpenAI API 호출
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = api_base or settings.OPENAI_API_BASE
        self.model = model or settings.OPENAI_MODEL
        
        if not self.api_key:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="OpenAI API key not configured"
            )
    
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        force_json: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> dict:
        """
        Chat Completion 호출
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            force_json: JSON 응답 강제 여부
            temperature: 온도 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            {
                "content": str,  # 응답 내용
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
            }
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # JSON 모드 강제
        if force_json:
            payload["response_format"] = {"type": "json_object"}
            # JSON 응답 힌트 추가
            if "json" not in user_prompt.lower():
                messages[-1]["content"] += "\n\nRespond in valid JSON format."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    
                    raise WorkflowError(
                        code=ErrorCode.LLM_API_ERROR,
                        message=f"OpenAI API error: {error_detail}",
                        details={
                            "status_code": response.status_code,
                            "error": error_detail
                        }
                    )
                
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                
                return {
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
                }
                
        except httpx.TimeoutException:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message="OpenAI API timeout",
                retryable=True
            )
        except httpx.RequestError as e:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message=f"OpenAI API request error: {str(e)}",
                details={"error": str(e)},
                retryable=True
            )
    
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
        """
        Vision Completion 호출 (GPT-4o Vision API)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            image_base64_list: base64 인코딩된 이미지 리스트
            force_json: JSON 응답 강제 여부
            temperature: 온도 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            model: 사용할 모델 (기본값: gpt-4o)
            
        Returns:
            {
                "content": str,  # 응답 내용
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
            }
        """
        # Vision 지원 모델 사용 (gpt-4o 또는 gpt-4o-mini)
        vision_model = model or "gpt-4o"
        
        # 이미지 content 구성
        content_parts = [{"type": "text", "text": user_prompt}]
        
        for img_base64 in image_base64_list:
            # data:image/png;base64, 형식인지 확인
            if not img_base64.startswith("data:"):
                img_base64 = f"data:image/png;base64,{img_base64}"
            
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": img_base64,
                    "detail": "high"  # high detail for better OCR
                }
            })
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_parts}
        ]
        
        payload = {
            "model": vision_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # JSON 모드 강제
        if force_json:
            payload["response_format"] = {"type": "json_object"}
            # JSON 응답 힌트 추가
            if "json" not in user_prompt.lower():
                content_parts[0]["text"] += "\n\nRespond in valid JSON format."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:  # Vision은 더 긴 타임아웃
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    
                    raise WorkflowError(
                        code=ErrorCode.LLM_API_ERROR,
                        message=f"OpenAI Vision API error: {error_detail}",
                        details={
                            "status_code": response.status_code,
                            "error": error_detail,
                            "model": vision_model
                        }
                    )
                
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                
                return {
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                    "model": vision_model
                }
                
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
