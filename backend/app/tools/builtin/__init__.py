"""
=============================================================================
빌트인 Tool 등록
=============================================================================

이 파일에서 모든 빌트인 Tool들을 import하고 BUILTIN_TOOLS 리스트에 등록합니다.

## 새 Tool 등록 방법

1. 새 Tool 파일을 app/tools/builtin/ 디렉토리에 생성
   예: app/tools/builtin/my_tools.py

2. BaseTool 또는 LLMTool을 상속받아 Tool 클래스 구현

3. 이 파일(__init__.py)에서 import 추가:
   from app.tools.builtin.my_tools import MyTool1, MyTool2

4. BUILTIN_TOOLS 리스트에 인스턴스 추가:
   BUILTIN_TOOLS = [
       ...
       MyTool1(),
       MyTool2(),
   ]

5. 서버 재시작 시 자동으로 등록됨

## 주의사항

- Tool 클래스가 아닌 인스턴스를 등록합니다: MyTool() (O), MyTool (X)
- tool_id는 유니크해야 합니다
- version이 다르면 같은 tool_id로 여러 버전 등록 가능

=============================================================================
"""

# =============================================================================
# PDF Tools
# =============================================================================
from app.tools.builtin.pdf_tools import (
    PDFExtractTool,
    PDFInfoTool,
    PDFToImagesTool,
    PDFVisionExtractTool,
)

# =============================================================================
# LLM Tools
# =============================================================================
from app.tools.builtin.llm_tools import (
    SummarizeTool,
    TranslateTool,
    ExtractInfoTool,
    AnalyzeTool,
    GenerateTool,
    VisionExtractTool,
)

# =============================================================================
# Text Tools
# =============================================================================
from app.tools.builtin.text_tools import (
    TextFormatTool,
    TextSplitTool,
    TextJoinTool,
    TextReplaceTool,
    TextTemplateTool,
    TextStatsTool,
    JSONParseTool,
)

# =============================================================================
# Data Tools
# =============================================================================
from app.tools.builtin.data_tools import (
    DataMapTool,
    DataFilterTool,
    DataMergeTool,
    DataSelectTool,
    DataTransformTool,
)

# =============================================================================
# Tool 등록 리스트
# =============================================================================
# 새 Tool을 추가하려면 아래 리스트에 인스턴스를 추가하세요

BUILTIN_TOOLS = [
    # =========================================
    # PDF Tools
    # =========================================
    # PDFExtractTool(),
    # PDFInfoTool(),
    # PDFToImagesTool(),
    PDFVisionExtractTool(),
    
    # =========================================
    # LLM Tools
    # =========================================
    SummarizeTool(),
    TranslateTool(),
    # ExtractInfoTool(),
    AnalyzeTool(),
    # GenerateTool(),
    # VisionExtractTool(),
    
    # =========================================
    # Text Tools
    # =========================================
    # TextFormatTool(),
    # TextSplitTool(),
    # TextJoinTool(),
    # TextReplaceTool(),
    # TextTemplateTool(),
    # TextStatsTool(),
    # JSONParseTool(),
    
    # =========================================
    # Data Tools
    # =========================================
    # DataMapTool(),
    # DataFilterTool(),
    # DataMergeTool(),
    # DataSelectTool(),
    # DataTransformTool(),
    
    # =========================================
    # 새로운 Tool을 여기에 추가하세요
    # =========================================
    # MyCustomTool(),
]


# =============================================================================
# 모든 Tool export
# =============================================================================
__all__ = [
    "BUILTIN_TOOLS",
    # PDF
    "PDFExtractTool",
    "PDFInfoTool",
    "PDFToImagesTool",
    "PDFVisionExtractTool",
    # LLM
    "SummarizeTool",
    "TranslateTool",
    "ExtractInfoTool",
    "AnalyzeTool",
    "GenerateTool",
    "VisionExtractTool",
    # Text
    "TextFormatTool",
    "TextSplitTool",
    "TextJoinTool",
    "TextReplaceTool",
    "TextTemplateTool",
    "TextStatsTool",
    "JSONParseTool",
    # Data
    "DataMapTool",
    "DataFilterTool",
    "DataMergeTool",
    "DataSelectTool",
    "DataTransformTool",
]
