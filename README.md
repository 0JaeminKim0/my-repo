# Workflow Tool Platform

LLM 기반 업무 자동화 플랫폼 - 관리자가 개발한 Tool을 연결하여 Workflow를 구성하고 실행합니다.

## 핵심 기능

1. **Tool 관리**: 미리 개발된 Tool(플러그인)을 조회하고 사용
2. **Workflow 빌더**: 여러 Tool을 선형으로 연결하여 업무 자동화
3. **Run 실행 & Trace**: Workflow 실행 및 Node별 상세 추적

## 기술 스택

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React + TypeScript + TailwindCSS
- **Database**: SQLite (SQLAlchemy async)
- **LLM**: OpenAI Chat Completions API
- **Deployment**: Railway (Single Service)

## 프로젝트 구조

```
webapp/
├── backend/
│   ├── app/
│   │   ├── api/              # API 엔드포인트
│   │   │   ├── tools.py      # Tool API
│   │   │   ├── workflows.py  # Workflow API
│   │   │   ├── runs.py       # Run API
│   │   │   └── files.py      # File Upload API
│   │   ├── core/             # 핵심 설정
│   │   │   ├── config.py     # 환경 설정
│   │   │   ├── database.py   # DB 설정
│   │   │   └── errors.py     # 에러 정의
│   │   ├── models/           # 데이터 모델
│   │   │   ├── schemas.py    # Pydantic 스키마
│   │   │   └── database.py   # SQLAlchemy 모델
│   │   ├── services/         # 비즈니스 로직
│   │   │   ├── llm_service.py      # OpenAI API
│   │   │   ├── file_service.py     # 파일 관리
│   │   │   └── workflow_engine.py  # Workflow 실행 엔진
│   │   ├── tools/            # Tool 시스템
│   │   │   ├── base.py       # Tool 기본 클래스 ⭐
│   │   │   ├── registry.py   # Tool 레지스트리
│   │   │   └── builtin/      # 빌트인 Tool ⭐
│   │   │       ├── __init__.py   # Tool 등록
│   │   │       ├── pdf_tools.py  # PDF Tool
│   │   │       ├── llm_tools.py  # LLM Tool
│   │   │       ├── text_tools.py # Text Tool
│   │   │       └── data_tools.py # Data Tool
│   │   └── main.py           # FastAPI 앱
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── services/         # API 클라이언트
│   │   ├── types/            # TypeScript 타입
│   │   └── App.tsx           # 메인 앱
│   └── package.json
├── Dockerfile
├── railway.json
└── README.md
```

## 새 Tool 개발 가이드 ⭐

### 1. Tool 파일 생성

`backend/app/tools/builtin/` 디렉토리에 새 파일을 생성합니다.

```python
# backend/app/tools/builtin/my_tools.py

from app.tools.base import BaseTool, ToolParameter, ToolParameterType

class MyCustomTool(BaseTool):
    """
    내 커스텀 Tool
    """
    
    # 필수: Tool 식별자
    tool_id = "my.custom_tool"
    version = "1.0.0"
    name = "My Custom Tool"
    description = "이 Tool은 XX를 수행합니다"
    category = "custom"  # 카테고리: file, llm, text, data, custom 등
    
    # 입력 스키마 정의
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
    
    # 출력 스키마 정의
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
    
    # 실행 로직 구현
    async def execute(self, inputs: dict, context: dict) -> dict:
        input_text = inputs.get("input_text", "")
        max_length = inputs.get("max_length", 100)
        
        # 실제 로직 구현
        result = input_text[:max_length]
        
        return {
            "result": result,
            "metadata": {
                "original_length": len(input_text),
                "truncated": len(input_text) > max_length
            }
        }
```

### 2. LLM Tool 개발 (프롬프트 사용)

```python
from app.tools.base import LLMTool, ToolParameter, ToolParameterType

class MyLLMTool(LLMTool):
    """
    LLM 기반 Tool - 프롬프트는 Workflow Node에서 설정
    """
    
    tool_id = "llm.my_tool"
    version = "1.0.0"
    name = "My LLM Tool"
    description = "LLM을 사용하여 XX를 수행합니다"
    category = "llm"
    
    # LLM Tool 기본 설정
    default_system_prompt = "You are a helpful assistant."
    default_temperature = 0.7
    default_max_tokens = 2000
    
    input_schema = [
        ToolParameter(
            name="text",
            type=ToolParameterType.STRING,
            description="처리할 텍스트",
            required=True
        )
    ]
    
    output_schema = [
        ToolParameter(
            name="result",
            type=ToolParameterType.STRING,
            description="LLM 응답"
        )
    ]
    
    # LLMTool은 execute()가 이미 구현되어 있음
    # 필요시 오버라이드 가능
```

### 3. Tool 등록

`backend/app/tools/builtin/__init__.py` 파일을 수정합니다.

```python
# Import 추가
from app.tools.builtin.my_tools import MyCustomTool, MyLLMTool

# BUILTIN_TOOLS 리스트에 추가
BUILTIN_TOOLS = [
    # ... 기존 Tool들 ...
    
    # 새로 추가
    MyCustomTool(),
    MyLLMTool(),
]
```

### 4. Context에서 사용 가능한 서비스

```python
async def execute(self, inputs: dict, context: dict) -> dict:
    # context에서 사용 가능한 서비스들
    
    # 1. LLM 서비스 (LLM API 호출)
    llm_service = context.get("llm_service")
    response = await llm_service.chat_completion(
        system_prompt="...",
        user_prompt="...",
        force_json=True
    )
    
    # 2. 파일 서비스 (업로드된 파일 조회)
    file_service = context.get("file_service")
    file_info = await file_service.get_file("file_ref_id")
    
    # 3. 실행 정보
    run_id = context.get("run_id")
    node_id = context.get("node_id")
    
    # 4. LLM Tool용 프롬프트 (Workflow Node에서 설정)
    prompt = context.get("prompt")  # {system, user, force_json}
```

## 로컬 개발

### Backend

```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정

# 서버 실행
python -m uvicorn app.main:app --reload --port 3000
```

### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드 (backend/static으로 출력)
npm run build
```

## API 문서

서버 실행 후 http://localhost:3000/docs 에서 Swagger UI 확인

### 주요 엔드포인트

- `GET /api/tools` - Tool 목록
- `GET /api/tools/{tool_id}` - Tool 상세
- `POST /api/workflows` - Workflow 생성
- `GET /api/workflows` - Workflow 목록
- `POST /api/runs` - Workflow 실행
- `GET /api/runs/{run_id}` - Run 상세 (Trace 포함)

## Railway 배포

1. Railway 프로젝트 생성
2. GitHub 레포지토리 연결
3. 환경변수 설정:
   - `OPENAI_API_KEY`: OpenAI API 키
   - `DATABASE_URL`: (선택) PostgreSQL URL
4. 자동 배포 완료

## Workflow JSON 예시

```json
{
  "name": "PDF Extract -> Summarize",
  "nodes": [
    {
      "node_id": "n1",
      "tool_id": "pdf.extract",
      "version": "1.0.0",
      "input_mapping": {
        "file_ref": { "type": "constant", "value": "file_abc123" },
        "mode": { "type": "constant", "value": "all" }
      }
    },
    {
      "node_id": "n2",
      "tool_id": "llm.summarize",
      "version": "1.0.0",
      "input_mapping": {
        "text": { "type": "fromNode", "node_id": "n1", "path": "extracted_text" }
      },
      "prompt": {
        "system": "You are a professional summarizer.",
        "user": "Summarize the following text in 3 bullet points:\n\n{{input.text}}",
        "force_json": true
      }
    }
  ]
}
```

## 라이선스

MIT
