"""
HistoK LangGraph Fuseki - 비동기 최적화 그래프

진정한 비동기 처리를 위한 개선된 그래프:
1. 조기 응답: 사용자에게 즉시 의도 확인 질문 제시
2. 백그라운드 처리: 사용자 선택과 동시에 키워드 확장, 엔티티 추출 시작
3. 점진적 완성: 기본 결과 → 확장 결과 → 최종 결과

플로우:
1. History Check (0.1초)
2. Quick Classify (0.2초) 
3. 조기 응답: 사용자 의도 확인 질문 제시 (0.3초 총 소요)
4. 백그라운드 시작:
   - Thread 1: 키워드 확장 (LLM)
   - Thread 2: 기본 엔티티 추출 (TTL)
   - Thread 3: 벡터 검색 준비
5. 사용자 선택 완료 시 백그라운드 결과 통합
"""

import os
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, END
from backend.langgraph_fuseki.state import GraphState

# 노드 import
from backend.langgraph_fuseki.nodes.history_check_node import history_check_node
from backend.langgraph_fuseki.nodes.classify_node import query_classifier_node


class AsyncGraphExecutor:
    """비동기 그래프 실행기"""

    def __init__(self):
        self.background_tasks = {}
        self.executor = None

    def __enter__(self):
        """Context manager 진입"""
        self.executor = ThreadPoolExecutor(max_workers=4)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.shutdown()
        return False

    def shutdown(self):
        """ThreadPoolExecutor 명시적 종료"""
        if self.executor is not None:
            try:
                self.executor.shutdown(wait=True, cancel_futures=True)
            except Exception as e:
                print(f"[WARN] Executor shutdown 오류: {e}")
            finally:
                self.executor = None

    def __del__(self):
        """소멸자에서도 안전하게 종료"""
        self.shutdown()
    
    def start_background_processing(self, state: GraphState) -> Dict[str, Any]:
        """
        3단계 파이프라인: Phase 2 백그라운드 처리 시작 (Thread 기반)

        동시 실행:
        1. Stage 1-B: 상세 분석 (LLM 2회 병렬)
        2. Entity 준비: TTL 로드 + 기본 매칭
        3. Vector 검색
        """
        query = state.get("query", "")

        # Executor가 없으면 초기화
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=4)

        # 백그라운드 작업들
        results = {}
        threads = {}

        # 결과를 저장할 공유 딕셔너리
        import threading
        results_lock = threading.Lock()

        # Thread 1: Stage 1-B (상세 분석)
        def run_stage1b_detailed():
            from backend.langgraph_fuseki.nodes.classify_node import query_classifier_stage1b_background
            result = query_classifier_stage1b_background(state)
            with results_lock:
                results["stage1b_detailed"] = result

        # Thread 2: Entity 준비 (TTL 로드 + 기본 매칭)
        def run_entity_preparation():
            result = self._background_entity_preparation(query, state)
            with results_lock:
                results["entity_preparation"] = result

        # Thread 3: Vector 검색
        def run_vector_search():
            result = self._background_vector_search(query, state)
            with results_lock:
                results["vector_search"] = result

        # 스레드 시작 (daemon=False로 변경하여 안전한 종료 보장)
        threads["stage1b_detailed"] = threading.Thread(target=run_stage1b_detailed, daemon=False)
        threads["entity_preparation"] = threading.Thread(target=run_entity_preparation, daemon=False)
        threads["vector_search"] = threading.Thread(target=run_vector_search, daemon=False)

        for thread in threads.values():
            thread.start()

        return {"threads": threads, "results": results, "results_lock": results_lock}
    
    def _background_entity_preparation(self, query: str, state: GraphState) -> Dict[str, Any]:
        """
        백그라운드 Entity 준비: TTL 로드 + 기본 매칭

        Stage 1-A에서 추출된 basic_keywords를 사용하여 TTL 매칭
        """
        try:
            from backend.langgraph_fuseki.nodes.entity_expander_node import load_ttl_entities

            print("  ├─ [BACKGROUND] Entity 준비 (TTL 로드 + 기본 매칭) 시작...")
            start_time = time.time()

            # TTL 데이터 로드
            ttl_data = load_ttl_entities()

            # Stage 1-A에서 추출된 키워드 사용
            basic_keywords = state.get("basic_keywords", [])
            matched_entities = []
            seen = set()

            for keyword in basic_keywords:
                if keyword in ttl_data["label_to_uri"]:
                    uri = ttl_data["label_to_uri"][keyword]
                    entity_type = ttl_data["uri_to_type"].get(uri, "Event")
                    key = uri or keyword
                    if key not in seen:
                        seen.add(key)
                        matched_entities.append({
                            "type": entity_type,
                            "name": keyword,
                            "uri": uri,
                            "matched": True,
                            "match_method": "exact_basic"
                        })

            elapsed = time.time() - start_time
            print(f"  ├─ [BACKGROUND] Entity 준비 완료: {len(matched_entities)}개 엔티티 ({elapsed:.2f}초)")

            return {
                "status": "success",
                "basic_entities": matched_entities,
                "ttl_data": ttl_data,
                "processing_time": elapsed
            }

        except Exception as e:
            print(f"  ├─ [BACKGROUND] Entity 준비 실패: {e}")
            return {"status": "error", "error": str(e)}

    def _background_vector_search(self, query: str, state: GraphState) -> Dict[str, Any]:
        """
        백그라운드 Vector 검색

        Stage 1-A에서 추출된 basic_keywords로 pgvector 검색
        """
        try:
            from backend.langgraph_fuseki.nodes.entity_expander_node import (
                search_entities_with_pgvector
            )

            print("  ├─ [BACKGROUND] Vector 검색 시작...")
            start_time = time.time()

            # Stage 1-A에서 추출된 키워드 사용
            basic_keywords = state.get("basic_keywords", [])

            # TTL 데이터 (Entity 준비에서 로드됨, 없으면 대기)
            ttl_data = state.get("ttl_data", {})

            if not ttl_data:
                # TTL 데이터 없으면 직접 로드
                from backend.langgraph_fuseki.nodes.entity_expander_node import load_ttl_entities
                ttl_data = load_ttl_entities()

            # Pgvector 검색
            vector_results = []
            if basic_keywords and ttl_data:
                vector_results = search_entities_with_pgvector(
                    basic_keywords,
                    ttl_data,
                    top_k=10
                )

            elapsed = time.time() - start_time
            print(f"  ├─ [BACKGROUND] Vector 검색 완료: {len(vector_results)}개 ({elapsed:.2f}초)")

            return {
                "status": "success",
                "vector_results": vector_results,
                "processing_time": elapsed
            }

        except Exception as e:
            print(f"  ├─ [BACKGROUND] Vector 검색 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def wait_and_integrate_results(self, background_data: Dict[str, Any], state: GraphState, timeout: float = 5.0) -> GraphState:
        """
        3단계 파이프라인: Phase 3 백그라운드 결과 통합

        사용자 선택 완료 후 백그라운드 결과를 state에 통합:
        1. Stage 1-B 결과 (정밀 query_type, 키워드 확장, 프로퍼티 그룹)
        2. Entity 준비 결과 (TTL 데이터, 기본 엔티티)
        3. Vector 검색 결과

        사용자 선택 속도에 유연하게 대응:
        - 빠른 선택: 백그라운드 대기 (남은 시간만)
        - 느린 선택: 즉시 통합 (대기 없음)
        """
        threads = background_data.get("threads", {})
        results = background_data.get("results", {})
        results_lock = background_data.get("results_lock")

        print(f"\n{'='*70}")
        print(f"[Phase 3] 백그라운드 결과 통합 (최대 {timeout}초 대기)")
        print(f"{'='*70}")

        # 스레드 완료 대기
        for name, thread in threads.items():
            try:
                remaining_time = timeout
                if thread.is_alive():
                    print(f"  ├─ {name} 대기 중...")
                    thread.join(timeout=remaining_time)

                    if thread.is_alive():
                        print(f"  │  └─ {name} 타임아웃 (계속 진행)")
                    else:
                        print(f"  │  └─ {name} 완료 ✅")
                else:
                    print(f"  ├─ {name} 이미 완료 ✅")

            except Exception as e:
                print(f"  ├─ {name} 오류: {e}")

        # 결과 통합
        with results_lock:
            final_results = dict(results)

        print(f"\n  ├─ [통합] 결과 병합 중...")

        # 1. Stage 1-B 결과 통합
        stage1b_result = final_results.get("stage1b_detailed", {})
        if stage1b_result.get("status") == "success":
            # query_type 업데이트 (초기 → 정밀)
            query_type_initial = state.get("query_type_initial", "causal")
            query_type_final = stage1b_result.get("query_type", query_type_initial)

            if query_type_initial != query_type_final:
                print(f"  │  ├─ query_type 업데이트: {query_type_initial} → {query_type_final}")

            state["query_type"] = query_type_final
            state["query_intent"] = stage1b_result.get("query_intent", "")
            state["selected_property_groups"] = stage1b_result.get("selected_property_groups", [])
            state["selected_properties"] = stage1b_result.get("selected_properties", [])
            state["expanded_keywords_dict"] = stage1b_result.get("expanded_keywords_dict", {})
            state["expanded_keywords"] = stage1b_result.get("expanded_keywords", [])

            # 토큰 사용량 누적
            from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
            for response in stage1b_result.get("token_responses", []):
                token_update = extract_and_accumulate_tokens(state, response)
                state.update(token_update)

            print(f"  │  ├─ Stage 1-B 통합 완료 (query_type={query_type_final})")
        else:
            # Stage 1-B 실패 시 초기값 유지
            print(f"  │  ├─ Stage 1-B 실패 - 초기값 유지 (query_type={state.get('query_type_initial', 'causal')})")
            state["query_type"] = state.get("query_type_initial", "causal")

        # 2. Entity 준비 결과 통합
        entity_result = final_results.get("entity_preparation", {})
        if entity_result.get("status") == "success":
            state["ttl_data"] = entity_result.get("ttl_data", {})
            basic_entities = entity_result.get("basic_entities", [])
            print(f"  │  ├─ Entity 준비 통합 완료 ({len(basic_entities)}개 기본 엔티티)")
        else:
            print(f"  │  ├─ Entity 준비 실패")

        # 3. Vector 검색 결과 통합
        vector_result = final_results.get("vector_search", {})
        vector_entities = []
        if vector_result.get("status") == "success":
            vector_entities = vector_result.get("vector_results", [])
            print(f"  │  ├─ Vector 검색 통합 완료 ({len(vector_entities)}개)")
        else:
            print(f"  │  ├─ Vector 검색 실패")

        # 4. 엔티티 통합 (기본 + 벡터, 중복 제거)
        final_entities = []
        seen_uris = set()

        # 기본 엔티티 추가
        if entity_result.get("status") == "success":
            for entity in entity_result.get("basic_entities", []):
                uri = entity.get("uri")
                if uri and uri not in seen_uris:
                    seen_uris.add(uri)
                    final_entities.append(entity)

        # 벡터 검색 결과 추가 (중복 제거)
        for entity in vector_entities:
            uri = entity.get("uri")
            if uri and uri not in seen_uris:
                seen_uris.add(uri)
                final_entities.append(entity)

        state["extracted_entities"] = final_entities

        print(f"  └─ [통합] 완료: {len(final_entities)}개 엔티티")
        print(f"{'='*70}\n")

        return state


def create_async_graph_flow() -> StateGraph:
    """
    3단계 파이프라인 비동기 최적화 그래프

    Phase 1: Stage 1-A (0.2초) → 즉시 재질문
    Phase 2: 백그라운드 (Stage 1-B + Entity 준비 + Vector 검색)
    Phase 3: 통합 → Stage 2 진행
    """

    print("[INFO] 3단계 파이프라인 비동기 그래프 사용")

    workflow = StateGraph(GraphState)
    executor = AsyncGraphExecutor()

    # ========== Phase 1: 초고속 재질문 준비 (0.3초) ==========

    def phase1_quick_start_node(state: GraphState) -> GraphState:
        """
        Phase 1: 초고속 재질문 준비 (0.3초)

        1. 역사 관련 여부 체크 (0.1초)
        2. Stage 1-A: 규칙 기반 빠른 분류 (0.2초)
        3. 백그라운드 처리 시작
        """
        start_time = time.time()

        print(f"\n{'='*70}")
        print(f"[Phase 1] 초고속 재질문 준비")
        print(f"{'='*70}")

        # 1. 역사 관련 여부 체크
        state = history_check_node(state)
        if not state.get("is_historical", True):
            return state

        # 2. Stage 1-A: 규칙 기반 빠른 분류
        from backend.langgraph_fuseki.nodes.classify_node import query_classifier_stage1a_node
        state = query_classifier_stage1a_node(state)

        # 3. 백그라운드 처리 시작 (Phase 2)
        background_data = executor.start_background_processing(state)
        state["background_data"] = background_data

        elapsed = time.time() - start_time
        print(f"\n[Phase 1] 완료 ({elapsed:.2f}초) - 사용자 재질문 표시 가능")
        print(f"{'='*70}")

        return state
    
    # ========== Phase 1.5: 사용자 의도 확인 (백그라운드와 병렬) ==========

    def phase1_5_user_intent_node(state: GraphState) -> GraphState:
        """
        Phase 1.5: 사용자 의도 확인 (백그라운드 처리와 병렬)

        사용자가 선택하는 동안 백그라운드에서:
        - Stage 1-B (정밀 분석)
        - Entity 준비 (TTL 로드 + 매칭)
        - Vector 검색
        모두 진행 중
        """
        from backend.langgraph_fuseki.nodes.user_intent_clarification_node import user_intent_clarification_node

        print(f"\n[Phase 1.5] 사용자 의도 확인 (백그라운드 처리 진행 중)")

        # 사용자 의도 확인 (이 시간 동안 백그라운드 처리 진행)
        state = user_intent_clarification_node(state)

        return state

    # ========== Phase 3: 백그라운드 결과 통합 ==========

    def phase3_integration_node(state: GraphState) -> GraphState:
        """
        Phase 3: 백그라운드 결과 통합

        사용자 선택 완료 후 백그라운드 결과를 state에 통합:
        1. Stage 1-B 결과 (정밀 query_type, 키워드 확장)
        2. Entity 준비 결과 (TTL 데이터, 기본 엔티티)
        3. Vector 검색 결과

        → Stage 2 (Entity Extractor)로 진행
        """
        background_data = state.get("background_data", {})

        if background_data:
            # 백그라운드 결과 통합 (최대 3초 대기)
            state = executor.wait_and_integrate_results(background_data, state, timeout=3.0)
        else:
            print(f"\n[Phase 3] 백그라운드 데이터 없음 - 건너뜀")

        return state

    # ========== Stage 2~6: 기존 파이프라인 ==========

    def final_processing_node(state: GraphState) -> GraphState:
        """
        Stage 2~6: 기존 파이프라인 (순차 실행)

        Stage 2: Entity Extractor (완성)
        Stage 3: Semantic Expander
        Stage 4: Knowledge Retrieval
        Stage 5: Path Evidence Aggregator
        Stage 6: Story Generator
        """
        from backend.langgraph_fuseki.nodes.entity_expander_node import entity_expander_node
        from backend.langgraph_fuseki.nodes.kg.semantic_expander_node import semantic_expander_node
        from backend.langgraph_fuseki.nodes.kg.parallel_knowledge_retrieval_node import parallel_knowledge_retrieval_node
        from backend.langgraph_fuseki.nodes.kg.path_evidence_aggregator_node import path_evidence_aggregator_node
        from backend.langgraph_fuseki.nodes.generate_node import story_generator_node

        print(f"\n[Stage 2~6] 최종 처리 시작")

        # Stage 2: Entity Extractor (이미 기본 엔티티는 있으므로 추가 확장만)
        state = entity_expander_node(state)

        # Stage 3~6: 순차 실행
        state = semantic_expander_node(state)
        state = parallel_knowledge_retrieval_node(state)
        state = path_evidence_aggregator_node(state)
        state = story_generator_node(state)

        return state
    
    # ========== 노드 등록 ==========
    workflow.add_node("phase1_quick_start", phase1_quick_start_node)
    workflow.add_node("phase1_5_user_intent", phase1_5_user_intent_node)
    workflow.add_node("phase3_integration", phase3_integration_node)
    workflow.add_node("final_processing", final_processing_node)

    # ========== 플로우 정의 ==========
    workflow.set_entry_point("phase1_quick_start")

    # 조건부 분기 1: Phase 1 → Phase 1.5 or Final
    def route_after_phase1(state: GraphState) -> str:
        """
        역사 질문이면 Phase 1.5 (사용자 의도 확인)
        비역사 질문이면 바로 Final (답변 생성)
        """
        if not state.get("is_historical", True):
            return "final_processing"  # 비역사 질문
        else:
            return "phase1_5_user_intent"  # 역사 질문

    workflow.add_conditional_edges(
        "phase1_quick_start",
        route_after_phase1,
        {
            "phase1_5_user_intent": "phase1_5_user_intent",
            "final_processing": "final_processing"
        }
    )

    # Phase 1.5 → Phase 3 (백그라운드 결과 통합)
    workflow.add_edge("phase1_5_user_intent", "phase3_integration")

    # Phase 3 → Final (Stage 2~6)
    workflow.add_edge("phase3_integration", "final_processing")

    # Final → END
    workflow.add_edge("final_processing", END)

    return workflow.compile()


# 비동기 그래프 인스턴스
async_graph = create_async_graph_flow()