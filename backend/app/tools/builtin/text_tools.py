"""
=============================================================================
텍스트 처리 Tool들
=============================================================================

이 파일은 LLM 없이 텍스트를 처리하는 Tool들을 포함합니다.
단순한 텍스트 변환, 포맷팅, 분할 등의 작업을 수행합니다.

## 특징

- LLM 호출 없이 동작 (비용 없음)
- 빠른 실행 속도
- 결정적(deterministic) 결과

=============================================================================
"""

from app.tools.base import BaseTool, ToolParameter, ToolParameterType, WorkflowError, ErrorCode
import re
import json


class TextFormatTool(BaseTool):
    """
    텍스트 포맷팅 Tool
    
    텍스트를 다양한 형식으로 변환합니다.
    """
    
    tool_id = "text.format"
    version = "1.0.0"
    name = "Text Formatter"
    description = "텍스트를 다양한 형식으로 변환합니다"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="변환할 텍스트",
            required=True
        ),
        ToolParameter(
            name="format",
            type=ToolParameterType.STRING,
            description="포맷: 'uppercase', 'lowercase', 'titlecase', 'trim', 'slug'",
            required=False,
            default="trim"
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="formatted",
            type=ToolParameterType.STRING,
            description="변환된 텍스트"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        text = inputs.get("text", "")
        format_type = inputs.get("format", "trim")
        
        if format_type == "uppercase":
            result = text.upper()
        elif format_type == "lowercase":
            result = text.lower()
        elif format_type == "titlecase":
            result = text.title()
        elif format_type == "trim":
            result = text.strip()
        elif format_type == "slug":
            # URL 슬러그 형식으로 변환
            result = re.sub(r'[^\w\s-]', '', text.lower())
            result = re.sub(r'[-\s]+', '-', result).strip('-')
        else:
            result = text
        
        return {"formatted": result}


class TextSplitTool(BaseTool):
    """
    텍스트 분할 Tool
    
    텍스트를 지정된 구분자 또는 길이로 분할합니다.
    """
    
    tool_id = "text.split"
    version = "1.0.0"
    name = "Text Splitter"
    description = "텍스트를 분할합니다"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="분할할 텍스트",
            required=True
        ),
        ToolParameter(
            name="mode",
            type=ToolParameterType.STRING,
            description="분할 모드: 'delimiter', 'lines', 'chunks'",
            required=False,
            default="lines"
        ),
        ToolParameter(
            name="delimiter",
            type=ToolParameterType.STRING,
            description="구분자 (mode='delimiter'일 때)",
            required=False,
            default=","
        ),
        ToolParameter(
            name="chunk_size",
            type=ToolParameterType.INTEGER,
            description="청크 크기 (mode='chunks'일 때)",
            required=False,
            default=1000
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="parts",
            type=ToolParameterType.ARRAY,
            description="분할된 텍스트 배열"
        ),
        ToolParameter(
            name="count",
            type=ToolParameterType.INTEGER,
            description="분할된 개수"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        text = inputs.get("text", "")
        mode = inputs.get("mode", "lines")
        delimiter = inputs.get("delimiter", ",")
        chunk_size = inputs.get("chunk_size", 1000)
        
        if mode == "delimiter":
            parts = [p.strip() for p in text.split(delimiter)]
        elif mode == "lines":
            parts = [line.strip() for line in text.split("\n") if line.strip()]
        elif mode == "chunks":
            parts = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        else:
            parts = [text]
        
        return {"parts": parts, "count": len(parts)}


class TextJoinTool(BaseTool):
    """
    텍스트 병합 Tool
    
    여러 텍스트를 하나로 병합합니다.
    """
    
    tool_id = "text.join"
    version = "1.0.0"
    name = "Text Joiner"
    description = "여러 텍스트를 병합합니다"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="parts",
            type=ToolParameterType.ARRAY,
            description="병합할 텍스트 배열",
            required=True
        ),
        ToolParameter(
            name="separator",
            type=ToolParameterType.STRING,
            description="구분자",
            required=False,
            default="\n"
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="joined",
            type=ToolParameterType.STRING,
            description="병합된 텍스트"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        parts = inputs.get("parts", [])
        separator = inputs.get("separator", "\n")
        
        # 문자열로 변환
        str_parts = [str(p) for p in parts]
        joined = separator.join(str_parts)
        
        return {"joined": joined}


class TextReplaceTool(BaseTool):
    """
    텍스트 치환 Tool
    
    텍스트 내 패턴을 치환합니다.
    """
    
    tool_id = "text.replace"
    version = "1.0.0"
    name = "Text Replacer"
    description = "텍스트 내 패턴을 치환합니다"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="대상 텍스트",
            required=True
        ),
        ToolParameter(
            name="pattern",
            type=ToolParameterType.STRING,
            description="찾을 패턴 (문자열 또는 정규식)",
            required=True
        ),
        ToolParameter(
            name="replacement",
            type=ToolParameterType.STRING,
            description="치환할 텍스트",
            required=True
        ),
        ToolParameter(
            name="use_regex",
            type=ToolParameterType.BOOLEAN,
            description="정규식 사용 여부",
            required=False,
            default=False
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="replaced",
            type=ToolParameterType.STRING,
            description="치환된 텍스트"
        ),
        ToolParameter(
            name="count",
            type=ToolParameterType.INTEGER,
            description="치환된 횟수"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        text = inputs.get("text", "")
        pattern = inputs.get("pattern", "")
        replacement = inputs.get("replacement", "")
        use_regex = inputs.get("use_regex", False)
        
        if use_regex:
            replaced, count = re.subn(pattern, replacement, text)
        else:
            count = text.count(pattern)
            replaced = text.replace(pattern, replacement)
        
        return {"replaced": replaced, "count": count}


class TextTemplateTool(BaseTool):
    """
    템플릿 렌더링 Tool
    
    템플릿에 변수를 치환하여 텍스트를 생성합니다.
    {{variable}} 형식의 플레이스홀더를 지원합니다.
    """
    
    tool_id = "text.template"
    version = "1.0.0"
    name = "Text Template"
    description = "템플릿에 변수를 치환합니다"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="template",
            type=ToolParameterType.STRING,
            description="템플릿 ({{variable}} 형식)",
            required=True
        ),
        ToolParameter(
            name="variables",
            type=ToolParameterType.OBJECT,
            description="치환할 변수들 (key-value)",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="rendered",
            type=ToolParameterType.STRING,
            description="렌더링된 텍스트"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        template = inputs.get("template", "")
        variables = inputs.get("variables", {})
        
        def replace_var(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))
        
        rendered = re.sub(r"\{\{([^}]+)\}\}", replace_var, template)
        
        return {"rendered": rendered}


class TextStatsTool(BaseTool):
    """
    텍스트 통계 Tool
    
    텍스트의 통계 정보를 계산합니다.
    """
    
    tool_id = "text.stats"
    version = "1.0.0"
    name = "Text Statistics"
    description = "텍스트의 통계 정보를 계산합니다"
    category = "text"
    
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
            name="stats",
            type=ToolParameterType.OBJECT,
            description="통계 정보"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        text = inputs.get("text", "")
        
        # 단어 분리
        words = re.findall(r'\b\w+\b', text)
        
        # 문장 분리
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 줄 분리
        lines = text.split('\n')
        lines = [l for l in lines if l.strip()]
        
        return {
            "stats": {
                "char_count": len(text),
                "char_count_no_spaces": len(text.replace(" ", "").replace("\n", "")),
                "word_count": len(words),
                "sentence_count": len(sentences),
                "line_count": len(lines),
                "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0
            }
        }


class JSONParseTool(BaseTool):
    """
    JSON 파싱 Tool
    
    JSON 문자열을 파싱하거나 객체를 JSON 문자열로 변환합니다.
    """
    
    tool_id = "text.json"
    version = "1.0.0"
    name = "JSON Parser"
    description = "JSON 파싱 및 직렬화"
    category = "text"
    
    input_schema = [
        ToolParameter(
            name="input",
            type=ToolParameterType.STRING,
            description="JSON 문자열 또는 객체",
            required=True
        ),
        ToolParameter(
            name="mode",
            type=ToolParameterType.STRING,
            description="모드: 'parse' (문자열→객체) 또는 'stringify' (객체→문자열)",
            required=False,
            default="parse"
        ),
        ToolParameter(
            name="path",
            type=ToolParameterType.STRING,
            description="추출할 경로 (dot notation, 예: 'data.items')",
            required=False,
            default=""
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.OBJECT,
            description="파싱/직렬화 결과"
        )
    ]
    
    async def execute(self, inputs: dict, context: dict) -> dict:
        input_data = inputs.get("input", "")
        mode = inputs.get("mode", "parse")
        path = inputs.get("path", "")
        
        try:
            if mode == "parse":
                if isinstance(input_data, str):
                    parsed = json.loads(input_data)
                else:
                    parsed = input_data
                
                # 경로로 값 추출
                if path:
                    keys = path.split(".")
                    result = parsed
                    for key in keys:
                        if isinstance(result, dict):
                            result = result.get(key)
                        elif isinstance(result, list) and key.isdigit():
                            result = result[int(key)]
                        else:
                            result = None
                            break
                    return {"result": result}
                
                return {"result": parsed}
            
            elif mode == "stringify":
                if isinstance(input_data, str):
                    # 이미 문자열이면 그대로
                    return {"result": input_data}
                return {"result": json.dumps(input_data, ensure_ascii=False, indent=2)}
            
            else:
                return {"result": input_data}
                
        except json.JSONDecodeError as e:
            raise WorkflowError(
                code=ErrorCode.TOOL_INPUT_INVALID,
                message=f"Invalid JSON: {str(e)}",
                details={"error": str(e)}
            )


# =============================================================================
# 새로운 텍스트 Tool 추가 방법
# =============================================================================
#
# 1. BaseTool 클래스 상속
# 2. tool_id, version, name, description, category 정의
# 3. input_schema, output_schema 정의
# 4. execute() 메서드 구현
#
# 예시:
#
# class TextEncodeTool(BaseTool):
#     tool_id = "text.encode"
#     version = "1.0.0"
#     name = "Text Encoder"
#     description = "텍스트를 Base64 등으로 인코딩합니다"
#     category = "text"
#     
#     input_schema = [
#         ToolParameter(name="text", type=ToolParameterType.STRING, ...),
#         ToolParameter(name="encoding", type=ToolParameterType.STRING, ...),
#     ]
#     
#     output_schema = [
#         ToolParameter(name="encoded", type=ToolParameterType.STRING, ...),
#     ]
#     
#     async def execute(self, inputs: dict, context: dict) -> dict:
#         import base64
#         text = inputs.get("text", "")
#         encoding = inputs.get("encoding", "base64")
#         
#         if encoding == "base64":
#             encoded = base64.b64encode(text.encode()).decode()
#         else:
#             encoded = text
#         
#         return {"encoded": encoded}
#
# =============================================================================
