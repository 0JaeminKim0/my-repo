"""
=============================================================================
PDF 관련 Tool들
=============================================================================

이 파일은 PDF 처리 관련 Tool들을 포함합니다.

## 새 PDF Tool 추가 방법

1. BaseTool 또는 기존 Tool을 상속
2. tool_id, version, name, description 정의
3. input_schema, output_schema 정의
4. execute() 메서드 구현
5. __init__.py의 BUILTIN_TOOLS에 추가

=============================================================================
"""

from app.tools.base import BaseTool, ToolParameter, ToolParameterType, WorkflowError, ErrorCode
from typing import Any
import os
import base64
import json
import httpx


class PDFExtractTool(BaseTool):
    """
    PDF 텍스트 추출 Tool
    
    PDF 파일에서 텍스트를 추출합니다.
    페이지 범위를 지정할 수 있습니다.
    
    Input:
        - file_ref: 업로드된 파일 참조 ID
        - mode: 추출 모드 ("all" | "pages")
        - pages.start: 시작 페이지 (mode="pages"일 때)
        - pages.end: 끝 페이지 (mode="pages"일 때)
    
    Output:
        - extracted_text: 추출된 텍스트
        - meta: 메타데이터 (page_count, char_count 등)
    """
    
    tool_id = "pdf.extract"
    version = "1.0.0"
    name = "PDF Text Extractor"
    description = "PDF 파일에서 텍스트를 추출합니다"
    category = "file"
    
    input_schema = [
        ToolParameter(
            name="file_ref",
            type=ToolParameterType.STRING,
            description="업로드된 PDF 파일 참조 ID",
            required=True
        ),
        ToolParameter(
            name="mode",
            type=ToolParameterType.STRING,
            description="추출 모드: 'all' (전체) 또는 'pages' (페이지 범위)",
            required=False,
            default="all"
        ),
        ToolParameter(
            name="pages.start",
            type=ToolParameterType.INTEGER,
            description="시작 페이지 번호 (1부터 시작)",
            required=False,
            default=1
        ),
        ToolParameter(
            name="pages.end",
            type=ToolParameterType.INTEGER,
            description="끝 페이지 번호",
            required=False,
            default=None
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="extracted_text",
            type=ToolParameterType.STRING,
            description="추출된 텍스트"
        ),
        ToolParameter(
            name="meta",
            type=ToolParameterType.OBJECT,
            description="메타데이터 (page_count, char_count, extracted_pages)"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        """PDF에서 텍스트 추출"""
        file_ref = inputs.get("file_ref")
        mode = inputs.get("mode", "all")
        start_page = inputs.get("pages.start", 1)
        end_page = inputs.get("pages.end")
        
        # 파일 경로 조회
        file_service = context.get("file_service")
        if not file_service:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="File service not available"
            )
        
        file_info = await file_service.get_file(file_ref)
        if not file_info:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File not found: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        filepath = file_info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File path not accessible: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(filepath)
            total_pages = len(reader.pages)
            
            # 페이지 범위 결정
            if mode == "pages":
                start_idx = max(0, start_page - 1)
                end_idx = min(total_pages, end_page) if end_page else total_pages
            else:
                start_idx = 0
                end_idx = total_pages
            
            # 텍스트 추출
            extracted_text = ""
            for i in range(start_idx, end_idx):
                page = reader.pages[i]
                text = page.extract_text() or ""
                extracted_text += f"\n--- Page {i + 1} ---\n{text}"
            
            extracted_text = extracted_text.strip()
            
            return {
                "extracted_text": extracted_text,
                "meta": {
                    "page_count": total_pages,
                    "char_count": len(extracted_text),
                    "extracted_pages": list(range(start_idx + 1, end_idx + 1))
                }
            }
            
        except Exception as e:
            raise WorkflowError(
                code=ErrorCode.EXECUTION_FAILED,
                message=f"Failed to extract PDF: {str(e)}",
                details={"file_ref": file_ref, "error": str(e)}
            )


class PDFInfoTool(BaseTool):
    """
    PDF 정보 조회 Tool
    
    PDF 파일의 메타데이터를 조회합니다.
    """
    
    tool_id = "pdf.info"
    version = "1.0.0"
    name = "PDF Info"
    description = "PDF 파일의 메타데이터를 조회합니다"
    category = "file"
    
    input_schema = [
        ToolParameter(
            name="file_ref",
            type=ToolParameterType.STRING,
            description="업로드된 PDF 파일 참조 ID",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="info",
            type=ToolParameterType.OBJECT,
            description="PDF 정보 (page_count, title, author 등)"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        """PDF 정보 조회"""
        file_ref = inputs.get("file_ref")
        
        file_service = context.get("file_service")
        if not file_service:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="File service not available"
            )
        
        file_info = await file_service.get_file(file_ref)
        if not file_info:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File not found: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        filepath = file_info.get("filepath")
        
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(filepath)
            metadata = reader.metadata or {}
            
            return {
                "info": {
                    "page_count": len(reader.pages),
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "filename": file_info.get("filename", "")
                }
            }
            
        except Exception as e:
            raise WorkflowError(
                code=ErrorCode.EXECUTION_FAILED,
                message=f"Failed to read PDF info: {str(e)}",
                details={"file_ref": file_ref, "error": str(e)}
            )


class PDFVisionExtractTool(BaseTool):
    """
    PDF Vision Extract Tool (GPT-4o 기반)
    
    PDF를 이미지로 변환 후 GPT-4o Vision으로 분석합니다.
    스캔된 PDF, 표, 차트, 손글씨 등을 인식할 수 있습니다.
    
    사용자가 자연어 프롬프트로 추출 로직을 정의할 수 있습니다.
    
    Input:
        - file_ref: 업로드된 PDF 파일 참조 ID
        - prompt: 추출/분석 지시사항 (자연어)
        - pages: 분석할 페이지 (예: "1", "1-3", "all")
        - output_format: 출력 형식 ("text", "json")
    
    Output:
        - result: GPT-4o Vision 분석 결과
        - pages_analyzed: 분석된 페이지 수
    """
    
    tool_id = "pdf.vision_extract"
    version = "1.0.0"
    name = "PDF Vision Extractor (GPT-4o)"
    description = "PDF를 이미지로 변환 후 GPT-4o Vision으로 분석합니다. 스캔 PDF, 표, 차트, 손글씨 인식 가능."
    category = "file"
    has_prompt = False  # 프롬프트는 input으로 직접 받음
    
    input_schema = [
        ToolParameter(
            name="file_ref",
            type=ToolParameterType.STRING,
            description="업로드된 PDF 파일 참조 ID",
            required=True
        ),
        ToolParameter(
            name="prompt",
            type=ToolParameterType.STRING,
            description="추출/분석 지시사항 (예: '이 문서에서 계약 금액과 날짜를 추출해줘')",
            required=True
        ),
        ToolParameter(
            name="pages",
            type=ToolParameterType.STRING,
            description="분석할 페이지: '1', '1-3', 'all' (기본값: '1')",
            required=False,
            default="1"
        ),
        ToolParameter(
            name="output_format",
            type=ToolParameterType.STRING,
            description="출력 형식: 'text' 또는 'json' (기본값: 'json')",
            required=False,
            default="json"
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.OBJECT,
            description="GPT-4o Vision 분석 결과"
        ),
        ToolParameter(
            name="raw_text",
            type=ToolParameterType.STRING,
            description="원본 텍스트 응답"
        ),
        ToolParameter(
            name="pages_analyzed",
            type=ToolParameterType.INTEGER,
            description="분석된 페이지 수"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        """PDF Vision 분석 실행"""
        file_ref = inputs.get("file_ref")
        prompt = inputs.get("prompt", "")
        pages_input = inputs.get("pages", "1")
        output_format = inputs.get("output_format", "json")
        
        # 파일 서비스
        file_service = context.get("file_service")
        if not file_service:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="File service not available"
            )
        
        file_info = await file_service.get_file(file_ref)
        if not file_info:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File not found: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        filepath = file_info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File path not accessible: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        # PDF를 이미지로 변환
        try:
            images_base64 = await self._pdf_to_images(filepath, pages_input)
        except Exception as e:
            raise WorkflowError(
                code=ErrorCode.EXECUTION_FAILED,
                message=f"Failed to convert PDF to images: {str(e)}",
                details={"error": str(e)}
            )
        
        if not images_base64:
            raise WorkflowError(
                code=ErrorCode.EXECUTION_FAILED,
                message="No pages to analyze"
            )
        
        # GPT-4o Vision API 호출
        try:
            result = await self._call_vision_api(
                images_base64=images_base64,
                prompt=prompt,
                output_format=output_format,
                context=context
            )
        except Exception as e:
            raise WorkflowError(
                code=ErrorCode.LLM_API_ERROR,
                message=f"Vision API error: {str(e)}",
                details={"error": str(e)}
            )
        
        return {
            "result": result.get("parsed", result.get("raw", "")),
            "raw_text": result.get("raw", ""),
            "pages_analyzed": len(images_base64)
        }
    
    async def _pdf_to_images(self, filepath: str, pages_input: str) -> list[str]:
        """PDF를 이미지로 변환하고 base64로 인코딩"""
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        
        # 페이지 범위 파싱
        if pages_input.lower() == "all":
            first_page = None
            last_page = None
        elif "-" in pages_input:
            parts = pages_input.split("-")
            first_page = int(parts[0])
            last_page = int(parts[1])
        else:
            first_page = int(pages_input)
            last_page = int(pages_input)
        
        # PDF를 이미지로 변환 (DPI 150으로 적당한 품질)
        convert_kwargs = {"dpi": 150}
        if first_page:
            convert_kwargs["first_page"] = first_page
        if last_page:
            convert_kwargs["last_page"] = last_page
        
        try:
            images = convert_from_path(filepath, **convert_kwargs)
        except Exception as e:
            # poppler가 없는 경우 PyMuPDF 시도
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(filepath)
                images = []
                
                start_idx = (first_page - 1) if first_page else 0
                end_idx = last_page if last_page else len(doc)
                
                for i in range(start_idx, min(end_idx, len(doc))):
                    page = doc[i]
                    mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    images.append(img)
                
                doc.close()
            except ImportError:
                raise WorkflowError(
                    code=ErrorCode.EXECUTION_FAILED,
                    message="PDF to image conversion failed. Install poppler or PyMuPDF.",
                    details={"original_error": str(e)}
                )
        
        # 이미지를 base64로 인코딩
        images_base64 = []
        for img in images:
            # 이미지 크기 제한 (최대 2000px)
            max_size = 2000
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # PNG로 인코딩
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            
            img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            images_base64.append(img_base64)
        
        return images_base64
    
    async def _call_vision_api(
        self,
        images_base64: list[str],
        prompt: str,
        output_format: str,
        context: dict
    ) -> dict:
        """GPT-4o Vision API 호출"""
        from app.core.config import settings
        
        api_key = settings.OPENAI_API_KEY
        api_base = settings.OPENAI_API_BASE
        
        if not api_key:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="OpenAI API key not configured"
            )
        
        # 시스템 프롬프트 구성
        system_prompt = """You are an expert document analyzer. 
Analyze the provided PDF page images and extract information as requested.
Be thorough and accurate. If you can't find certain information, explicitly state that."""
        
        if output_format == "json":
            system_prompt += "\n\nIMPORTANT: Respond in valid JSON format only."
        
        # 메시지 구성 (이미지들 포함)
        content = [{"type": "text", "text": prompt}]
        
        for i, img_base64 in enumerate(images_base64):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                    "detail": "high"
                }
            })
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        payload = {
            "model": "gpt-4o",  # GPT-4o Vision
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.2
        }
        
        if output_format == "json":
            payload["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{api_base}/chat/completions",
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
                    details={"status_code": response.status_code}
                )
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 토큰 사용량 기록
            usage = result.get("usage", {})
            context["token_usage"] = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            # JSON 파싱 시도
            parsed = None
            if output_format == "json":
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    parsed = {"raw_response": content}
            
            return {
                "raw": content,
                "parsed": parsed if parsed else content
            }


class PDFToImagesTool(BaseTool):
    """
    PDF to Images Tool
    
    PDF 파일을 이미지로 변환합니다.
    다른 Vision Tool과 연결하여 사용할 수 있습니다.
    """
    
    tool_id = "pdf.to_images"
    version = "1.0.0"
    name = "PDF to Images"
    description = "PDF 파일을 이미지(base64)로 변환합니다"
    category = "file"
    
    input_schema = [
        ToolParameter(
            name="file_ref",
            type=ToolParameterType.STRING,
            description="업로드된 PDF 파일 참조 ID",
            required=True
        ),
        ToolParameter(
            name="pages",
            type=ToolParameterType.STRING,
            description="변환할 페이지: '1', '1-3', 'all' (기본값: 'all')",
            required=False,
            default="all"
        ),
        ToolParameter(
            name="dpi",
            type=ToolParameterType.INTEGER,
            description="이미지 해상도 DPI (기본값: 150)",
            required=False,
            default=150
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="images",
            type=ToolParameterType.ARRAY,
            description="base64 인코딩된 이미지 배열"
        ),
        ToolParameter(
            name="page_count",
            type=ToolParameterType.INTEGER,
            description="변환된 페이지 수"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        """PDF를 이미지로 변환"""
        file_ref = inputs.get("file_ref")
        pages_input = inputs.get("pages", "all")
        dpi = inputs.get("dpi", 150)
        
        file_service = context.get("file_service")
        if not file_service:
            raise WorkflowError(
                code=ErrorCode.INTERNAL_ERROR,
                message="File service not available"
            )
        
        file_info = await file_service.get_file(file_ref)
        if not file_info:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File not found: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        filepath = file_info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"File path not accessible: {file_ref}",
                details={"file_ref": file_ref}
            )
        
        try:
            from pdf2image import convert_from_path
            from PIL import Image
            import io
            
            # 페이지 범위 파싱
            convert_kwargs = {"dpi": dpi}
            if pages_input.lower() != "all":
                if "-" in pages_input:
                    parts = pages_input.split("-")
                    convert_kwargs["first_page"] = int(parts[0])
                    convert_kwargs["last_page"] = int(parts[1])
                else:
                    convert_kwargs["first_page"] = int(pages_input)
                    convert_kwargs["last_page"] = int(pages_input)
            
            images = convert_from_path(filepath, **convert_kwargs)
            
            # base64 인코딩
            images_base64 = []
            for img in images:
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
                images_base64.append(img_base64)
            
            return {
                "images": images_base64,
                "page_count": len(images_base64)
            }
            
        except Exception as e:
            raise WorkflowError(
                code=ErrorCode.EXECUTION_FAILED,
                message=f"Failed to convert PDF to images: {str(e)}",
                details={"error": str(e)}
            )
