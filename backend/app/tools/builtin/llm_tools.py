"""
=============================================================================
LLM 기반 Tool들
=============================================================================

이 파일은 OpenAI Chat Completions API를 사용하는 LLM Tool들을 포함합니다.

## LLM Tool 개발 가이드

LLM Tool은 LLMTool 기본 클래스를 상속받아 구현합니다.
프롬프트는 Workflow Node에서 설정하므로, Tool에서는 기본 설정만 정의합니다.

### 특징

1. Node의 prompt 설정 사용
   - system: 시스템 프롬프트
   - user: 사용자 프롬프트 ({{input.xxx}} 템플릿)
   - force_json: JSON 응답 강제

2. 자동 템플릿 렌더링
   - {{input.text}} -> inputs["text"] 값으로 치환
   - {{input.data.key}} -> inputs["data"]["key"] 값으로 치환

3. 토큰 사용량 자동 기록
   - context["token_usage"]에 저장됨

=============================================================================
"""

from app.tools.base import LLMTool, BaseTool, ToolParameter, ToolParameterType, WorkflowError, ErrorCode
from typing import Any


class SummarizeTool(LLMTool):
    """
    텍스트 요약 Tool
    
    LLM을 사용하여 텍스트를 요약합니다.
    Node에서 프롬프트를 설정하여 요약 스타일을 지정할 수 있습니다.
    
    Input:
        - text: 요약할 텍스트
    
    Output:
        - summary: 요약 결과 (force_json=true인 경우)
        - 또는 result: 요약 결과 (force_json=false인 경우)
    
    Node 프롬프트 예시:
        {
            "system": "You are a professional summarizer.",
            "user": "Summarize the following text in 3 bullet points:\\n\\n{{input.text}}",
            "force_json": true
        }
    """
    
    tool_id = "llm.summarize"
    version = "1.0.0"
    name = "Text Summarizer"
    description = "LLM을 사용하여 텍스트를 요약합니다"
    category = "llm"
    
    default_system_prompt = "You are a professional text summarizer. Provide clear and concise summaries."
    default_temperature = 0.5
    default_max_tokens = 1000
    
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
        ),
        ToolParameter(
            name="result",
            type=ToolParameterType.STRING,
            description="요약 결과 (대체 키)"
        )
    ]


class TranslateTool(LLMTool):
    """
    텍스트 번역 Tool
    
    LLM을 사용하여 텍스트를 번역합니다.
    """
    
    tool_id = "llm.translate"
    version = "1.0.0"
    name = "Text Translator"
    description = "LLM을 사용하여 텍스트를 번역합니다"
    category = "llm"
    
    default_system_prompt = "You are a professional translator. Translate accurately while maintaining the original meaning and tone."
    default_temperature = 0.3
    default_max_tokens = 2000
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="번역할 텍스트",
            required=True
        ),
        ToolParameter(
            name="target_language",
            type=ToolParameterType.STRING,
            description="대상 언어 (예: Korean, English, Japanese)",
            required=False,
            default="English"
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="translated",
            type=ToolParameterType.STRING,
            description="번역 결과"
        ),
        ToolParameter(
            name="result",
            type=ToolParameterType.STRING,
            description="번역 결과 (대체 키)"
        )
    ]


class ExtractInfoTool(LLMTool):
    """
    정보 추출 Tool
    
    LLM을 사용하여 텍스트에서 구조화된 정보를 추출합니다.
    Node의 프롬프트에서 추출할 정보의 형식을 JSON으로 정의합니다.
    
    Node 프롬프트 예시:
        {
            "system": "You extract structured information from text.",
            "user": "Extract the following from the text:\\n- name\\n- email\\n- phone\\n\\nText: {{input.text}}\\n\\nRespond in JSON format.",
            "force_json": true
        }
    """
    
    tool_id = "llm.extract"
    version = "1.0.0"
    name = "Information Extractor"
    description = "LLM을 사용하여 텍스트에서 구조화된 정보를 추출합니다"
    category = "llm"
    
    default_system_prompt = "You extract structured information from text. Always respond in valid JSON format."
    default_temperature = 0.2
    default_max_tokens = 1000
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="정보를 추출할 텍스트",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.OBJECT,
            description="추출된 정보 (JSON)"
        )
    ]


class AnalyzeTool(LLMTool):
    """
    텍스트 분석 Tool
    
    LLM을 사용하여 텍스트를 분석합니다.
    감성 분석, 키워드 추출, 카테고리 분류 등에 사용할 수 있습니다.
    """
    
    tool_id = "llm.analyze"
    version = "1.0.0"
    name = "Text Analyzer"
    description = "LLM을 사용하여 텍스트를 분석합니다"
    category = "llm"
    
    default_system_prompt = "You are an expert text analyst. Provide thorough and insightful analysis."
    default_temperature = 0.5
    default_max_tokens = 1500
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="분석할 텍스트",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="analysis",
            type=ToolParameterType.STRING,
            description="분석 결과"
        ),
        ToolParameter(
            name="result",
            type=ToolParameterType.OBJECT,
            description="분석 결과 (JSON, force_json=true인 경우)"
        )
    ]


class GenerateTool(LLMTool):
    """
    텍스트 생성 Tool
    
    LLM을 사용하여 텍스트를 생성합니다.
    이메일, 보고서, 글 등을 생성하는 데 사용합니다.
    """
    
    tool_id = "llm.generate"
    version = "1.0.0"
    name = "Text Generator"
    description = "LLM을 사용하여 텍스트를 생성합니다"
    category = "llm"
    
    default_system_prompt = "You are a professional content writer. Generate high-quality content based on the given instructions."
    default_temperature = 0.7
    default_max_tokens = 2000
    
    input_schema = [
        ToolParameter(
            name="prompt",
            type=ToolParameterType.STRING,
            description="생성 지시사항 또는 주제",
            required=True
        ),
        ToolParameter(
            name="context",
            type=ToolParameterType.STRING,
            description="추가 컨텍스트 (선택)",
            required=False,
            default=""
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="generated",
            type=ToolParameterType.STRING,
            description="생성된 텍스트"
        ),
        ToolParameter(
            name="result",
            type=ToolParameterType.STRING,
            description="생성된 텍스트 (대체 키)"
        )
    ]


# =============================================================================
# 새로운 LLM Tool 추가 방법
# =============================================================================
#
# 1. LLMTool 클래스 상속
# 2. tool_id, version, name, description 정의
# 3. input_schema, output_schema 정의
# 4. (선택) default_system_prompt, default_temperature, default_max_tokens 설정
#
# execute() 메서드는 LLMTool에서 이미 구현되어 있으므로
# 대부분의 경우 오버라이드할 필요가 없습니다.
#
# 예시:
#
# class QATool(LLMTool):
#     tool_id = "llm.qa"
#     version = "1.0.0"
#     name = "Question Answerer"
#     description = "질문에 대한 답변을 생성합니다"
#     category = "llm"
#     
#     default_system_prompt = "You answer questions based on the given context."
#     
#     input_schema = [
#         ToolParameter(name="question", type=ToolParameterType.STRING, ...),
#         ToolParameter(name="context", type=ToolParameterType.STRING, ...),
#     ]
#     
#     output_schema = [
#         ToolParameter(name="answer", type=ToolParameterType.STRING, ...),
#     ]
#
# =============================================================================
