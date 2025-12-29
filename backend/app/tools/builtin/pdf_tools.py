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


# =============================================================================
# 이 파일에 새로운 PDF Tool을 추가하세요
# =============================================================================
#
# 예시:
#
# class PDFMergeTool(BaseTool):
#     tool_id = "pdf.merge"
#     version = "1.0.0"
#     name = "PDF Merger"
#     description = "여러 PDF 파일을 병합합니다"
#     category = "file"
#     
#     input_schema = [...]
#     output_schema = [...]
#     
#     async def execute(self, inputs: dict, context: dict) -> dict:
#         ...
#
# =============================================================================
