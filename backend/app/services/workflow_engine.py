"""
=============================================================================
Workflow Engine - 핵심 실행 엔진
=============================================================================

PRD 6. Runtime: Run Context + Mapping Evaluator + Node Trace

이 모듈은 Workflow를 실행하는 핵심 엔진입니다.

주요 컴포넌트:
1. MappingEvaluator - input_mapping 평가 및 실제 입력값 생성
2. WorkflowEngine - Workflow 실행 및 Node Trace 관리

=============================================================================
"""

from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import (
    WorkflowNode, WorkflowResponse, InputMapping,
    ConstantMapping, FromNodeMapping, NodeTraceStatus,
    RunStatus, NodeTrace, NodeTraceError, RunCost
)
from app.models.database import RunModel, NodeTraceModel
from app.tools.registry import tool_registry
from app.services.llm_service import LLMService
from app.services.file_service import FileService
from app.core.errors import WorkflowError, ErrorCode
from app.core.config import settings


class MappingEvaluator:
    """
    PRD 6.2 Mapping Evaluator (필수 기능)
    
    실행 시 input_mapping을 평가하여 실제 Tool input 생성
    - fromNode 참조는 이전 노드만 가능
    - 경로 미존재 시 즉시 실패
    """
    
    def __init__(self, node_outputs: dict[str, dict]):
        """
        Args:
            node_outputs: 이전 노드들의 출력 결과
                {"n1": {"text": "..."}, "n2": {"summary": "..."}}
        """
        self.node_outputs = node_outputs
    
    def evaluate(
        self,
        input_mapping: dict[str, InputMapping],
        current_node_id: str
    ) -> dict:
        """
        input_mapping을 평가하여 실제 입력값 생성
        
        Args:
            input_mapping: Node의 input_mapping 정의
            current_node_id: 현재 노드 ID (검증용)
            
        Returns:
            실제 Tool input 딕셔너리
            
        Raises:
            WorkflowError: 매핑 평가 실패 시
        """
        result = {}
        
        for key, mapping in input_mapping.items():
            if isinstance(mapping, dict):
                # Pydantic 모델이 아닌 dict인 경우 변환
                mapping_type = mapping.get("type")
                if mapping_type == "constant":
                    mapping = ConstantMapping(**mapping)
                elif mapping_type == "fromNode":
                    mapping = FromNodeMapping(**mapping)
                else:
                    raise WorkflowError(
                        code=ErrorCode.MAPPING_INVALID,
                        message=f"Unknown mapping type: {mapping_type}",
                        details={"key": key, "mapping": mapping}
                    )
            
            value = self._evaluate_single(mapping, current_node_id, key)
            result[key] = value
        
        return result
    
    def _evaluate_single(
        self,
        mapping: InputMapping,
        current_node_id: str,
        key: str
    ) -> Any:
        """단일 매핑 평가"""
        
        if isinstance(mapping, ConstantMapping):
            return mapping.value
        
        elif isinstance(mapping, FromNodeMapping):
            return self._evaluate_from_node(mapping, current_node_id, key)
        
        else:
            raise WorkflowError(
                code=ErrorCode.MAPPING_INVALID,
                message=f"Unknown mapping type for key '{key}'",
                details={"key": key}
            )
    
    def _evaluate_from_node(
        self,
        mapping: FromNodeMapping,
        current_node_id: str,
        key: str
    ) -> Any:
        """
        fromNode 매핑 평가
        
        PRD 규칙:
        - fromNode 참조는 이전 노드만 가능
        - 경로 미존재 시 즉시 실패
        """
        ref_node_id = mapping.node_id
        path = mapping.path
        
        # 참조 노드 출력 확인
        if ref_node_id not in self.node_outputs:
            raise WorkflowError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"Referenced node '{ref_node_id}' not found or not executed yet",
                details={
                    "current_node": current_node_id,
                    "referenced_node": ref_node_id,
                    "key": key
                }
            )
        
        # dot-path로 값 추출
        node_output = self.node_outputs[ref_node_id]
        value = self._get_by_path(node_output, path)
        
        if value is None:
            # 경로가 존재하지 않으면 실패
            raise WorkflowError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"Path '{path}' not found in node '{ref_node_id}' output",
                details={
                    "current_node": current_node_id,
                    "referenced_node": ref_node_id,
                    "path": path,
                    "key": key,
                    "available_keys": list(node_output.keys()) if isinstance(node_output, dict) else []
                }
            )
        
        return value
    
    def _get_by_path(self, data: Any, path: str) -> Any:
        """
        dot-path로 중첩 값 가져오기
        
        예: "meta.chars" -> data["meta"]["chars"]
        """
        if not path:
            return data
        
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                if key in value:
                    value = value[key]
                else:
                    return None
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None
            else:
                return None
        
        return value


class WorkflowEngine:
    """
    Workflow 실행 엔진
    
    PRD 6.1 Run Context 관리
    PRD 6.3 Node Trace 기록
    PRD 7.1 Fail-fast 정책 적용
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = None
        self.file_service = None
    
    async def execute(
        self,
        run_id: str,
        workflow: WorkflowResponse,
        draft_override: Optional[dict] = None
    ) -> dict:
        """
        Workflow 실행
        
        Args:
            run_id: Run ID
            workflow: Workflow 정의
            draft_override: 선택적 오버라이드 (테스트용)
            
        Returns:
            {
                "status": RunStatus,
                "node_outputs": dict,
                "final_output": dict,
                "error": Optional[NodeTraceError],
                "traces": list[NodeTrace],
                "cost": RunCost
            }
        """
        # Run Context 초기화 (PRD 6.1)
        node_outputs: dict[str, dict] = {}
        traces: list[NodeTrace] = []
        total_cost = RunCost()
        
        # 서비스 초기화
        self.file_service = FileService(self.db)
        try:
            self.llm_service = LLMService()
        except WorkflowError:
            # OpenAI API 키가 없어도 일단 진행 (LLM Tool 사용 시 에러)
            self.llm_service = None
        
        # Run 시작 시간 기록
        run_model = await self._get_run(run_id)
        run_model.status = RunStatus.RUNNING
        run_model.started_at = datetime.utcnow()
        await self.db.commit()
        
        # 노드 목록 (draft 오버라이드 적용)
        nodes = workflow.nodes
        if draft_override and "nodes" in draft_override:
            nodes = draft_override["nodes"]
        
        try:
            # 선형 실행 (PRD 5.2 규칙)
            for node in nodes:
                node_trace = await self._execute_node(
                    node=node,
                    node_outputs=node_outputs,
                    run_id=run_id
                )
                traces.append(node_trace)
                
                # Fail-fast (PRD 7.1)
                if node_trace.status == NodeTraceStatus.FAILED:
                    # 즉시 중단
                    run_model.status = RunStatus.FAILED
                    run_model.error_json = node_trace.error.model_dump() if node_trace.error else None
                    run_model.ended_at = datetime.utcnow()
                    run_model.node_outputs_json = node_outputs
                    await self.db.commit()
                    
                    return {
                        "status": RunStatus.FAILED,
                        "node_outputs": node_outputs,
                        "final_output": None,
                        "error": node_trace.error,
                        "traces": traces,
                        "cost": total_cost
                    }
                
                # 토큰 사용량 집계
                if node_trace.output_summary.get("token_usage"):
                    usage = node_trace.output_summary["token_usage"]
                    total_cost.tokens += usage.get("total_tokens", 0)
                    total_cost.prompt_tokens += usage.get("prompt_tokens", 0)
                    total_cost.completion_tokens += usage.get("completion_tokens", 0)
            
            # 최종 출력 매핑
            final_output = None
            if workflow.final_output:
                final_output = self._map_final_output(
                    workflow.final_output,
                    node_outputs
                )
            
            # 성공 처리
            run_model.status = RunStatus.SUCCESS
            run_model.ended_at = datetime.utcnow()
            run_model.node_outputs_json = node_outputs
            run_model.final_output_json = final_output
            run_model.total_tokens = total_cost.tokens
            run_model.prompt_tokens = total_cost.prompt_tokens
            run_model.completion_tokens = total_cost.completion_tokens
            await self.db.commit()
            
            return {
                "status": RunStatus.SUCCESS,
                "node_outputs": node_outputs,
                "final_output": final_output,
                "error": None,
                "traces": traces,
                "cost": total_cost
            }
            
        except Exception as e:
            # 예상치 못한 에러
            error = NodeTraceError(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=str(e),
                details={"exception": type(e).__name__}
            )
            
            run_model.status = RunStatus.FAILED
            run_model.error_json = error.model_dump()
            run_model.ended_at = datetime.utcnow()
            run_model.node_outputs_json = node_outputs
            await self.db.commit()
            
            return {
                "status": RunStatus.FAILED,
                "node_outputs": node_outputs,
                "final_output": None,
                "error": error,
                "traces": traces,
                "cost": total_cost
            }
    
    async def _execute_node(
        self,
        node: WorkflowNode,
        node_outputs: dict[str, dict],
        run_id: str
    ) -> NodeTrace:
        """
        단일 Node 실행 및 Trace 기록
        
        PRD 6.3 Node Trace
        """
        # Node Trace 시작
        trace = NodeTrace(
            node_id=node.node_id,
            tool_id=node.tool_id,
            status=NodeTraceStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # DB에 Trace 기록
        trace_model = NodeTraceModel(
            run_id=run_id,
            node_id=node.node_id,
            tool_id=node.tool_id,
            status=NodeTraceStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        self.db.add(trace_model)
        await self.db.commit()
        
        try:
            # Tool 조회
            tool = tool_registry.get(node.tool_id, node.version)
            
            # Mapping 평가 (PRD 6.2)
            evaluator = MappingEvaluator(node_outputs)
            
            # node.input_mapping을 dict로 변환
            input_mapping_dict = {}
            if node.input_mapping:
                for key, mapping in node.input_mapping.items():
                    if hasattr(mapping, 'model_dump'):
                        input_mapping_dict[key] = mapping.model_dump()
                    else:
                        input_mapping_dict[key] = mapping
            
            actual_inputs = evaluator.evaluate(input_mapping_dict, node.node_id)
            
            # 실행 컨텍스트 구성
            context = {
                "run_id": run_id,
                "node_id": node.node_id,
                "settings": settings,
                "llm_service": self.llm_service,
                "file_service": self.file_service,
            }
            
            # LLM Tool인 경우 프롬프트 추가
            if node.prompt:
                context["prompt"] = {
                    "system": node.prompt.system,
                    "user": node.prompt.user,
                    "force_json": node.prompt.force_json
                }
            
            # Tool 실행
            output = await tool.run(actual_inputs, context)
            
            # Node 출력 저장
            node_outputs[node.node_id] = output
            
            # Trace 성공 업데이트
            trace.status = NodeTraceStatus.SUCCESS
            trace.ended_at = datetime.utcnow()
            trace.input_summary = self._summarize_data(actual_inputs)
            trace.output_summary = self._summarize_data(output)
            
            # 토큰 사용량 추가
            if "token_usage" in context:
                trace.output_summary["token_usage"] = context["token_usage"]
            
            # DB 업데이트
            trace_model.status = NodeTraceStatus.SUCCESS
            trace_model.ended_at = datetime.utcnow()
            trace_model.input_summary_json = trace.input_summary
            trace_model.output_summary_json = trace.output_summary
            await self.db.commit()
            
            return trace
            
        except WorkflowError as e:
            # 예상된 에러 (PRD 7.2 표준 에러 포맷)
            trace.status = NodeTraceStatus.FAILED
            trace.ended_at = datetime.utcnow()
            trace.error = NodeTraceError(
                code=e.code.value,
                message=e.message,
                details=e.details
            )
            
            trace_model.status = NodeTraceStatus.FAILED
            trace_model.ended_at = datetime.utcnow()
            trace_model.error_json = trace.error.model_dump()
            await self.db.commit()
            
            return trace
            
        except Exception as e:
            # 예상치 못한 에러
            trace.status = NodeTraceStatus.FAILED
            trace.ended_at = datetime.utcnow()
            trace.error = NodeTraceError(
                code=ErrorCode.EXECUTION_FAILED.value,
                message=str(e),
                details={"exception": type(e).__name__}
            )
            
            trace_model.status = NodeTraceStatus.FAILED
            trace_model.ended_at = datetime.utcnow()
            trace_model.error_json = trace.error.model_dump()
            await self.db.commit()
            
            return trace
    
    def _summarize_data(self, data: dict, max_length: int = 200) -> dict:
        """
        데이터 요약 (Trace용)
        
        긴 텍스트는 잘라서 표시
        """
        summary = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > max_length:
                summary[key] = value[:max_length] + "..."
            elif isinstance(value, (list, dict)):
                summary[key] = f"<{type(value).__name__} len={len(value)}>"
            else:
                summary[key] = value
        return summary
    
    def _map_final_output(
        self,
        final_output_config,
        node_outputs: dict[str, dict]
    ) -> dict:
        """최종 출력 매핑"""
        result = {}
        
        for key, mapping in final_output_config.mapping.items():
            node_id = mapping.node_id
            path = mapping.path
            
            if node_id in node_outputs:
                evaluator = MappingEvaluator(node_outputs)
                value = evaluator._get_by_path(node_outputs[node_id], path)
                result[key] = value
        
        return result
    
    async def _get_run(self, run_id: str) -> RunModel:
        """Run 모델 조회"""
        from sqlalchemy import select
        result = await self.db.execute(
            select(RunModel).where(RunModel.run_id == run_id)
        )
        return result.scalar_one()
