"""
Integrated Test Runner for Fuseki RAG System

모든 기능을 활성화하고 커스텀 가중치를 적용하여 테스트합니다.
- Semantic Expanders: 모두 ON (temporal, category, causal_chain, pgvector)
- Aggregator Threads: 모두 ON (5개 스레드)
- Entity Boost Mode: ON (exact_match 적용)
- Custom Weights: 분석 기반 최적 가중치 적용

Usage:
    # 모든 질문 테스트 (40개 질문: 외국인 20개 + 아이들 20개)
    python backend/ragas/fuseki/integrated_test_runner.py

    # 디버깅용 (3개 질문만)
    python backend/ragas/fuseki/integrated_test_runner.py --limit 3 --debug
"""

import sys
from pathlib import Path

# ===== PROJECT ROOT 설정 =====
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parents[3]  # SKN18-FINAL-3TEAM

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import argparse
import time
from typing import List, Dict, Any
from datetime import datetime

# Local imports
from backend.ragas.fuseki.ragas_metrics import (
    RagasMetricsLoader,
    extract_contexts_from_evidences,
    evaluate_with_ragas
)

# Langgraph imports
from backend.langgraph_fuseki.graph import create_graph_flow
from backend.langgraph_fuseki.state import GraphState


# =====================================================
# Custom Weights (분석 기반 최적화)
# =====================================================
OPTIMIZED_WEIGHTS = {
    # Semantic Expanders (모두 활성화, 가중치 조정)
    "semantic_expanders": {
        "temporal": 1.3,      # 시간 정보는 역사 질문에 매우 중요
        "category": 1.2,      # 카테고리 분류는 정확도 향상
        "causal_chain": 1.4,  # 인과관계는 역사 이해의 핵심 (가장 높음)
        "pgvector": 1.0       # 벡터 검색은 기본 가중치
    },

    # Aggregator Threads (모두 활성화, 분석 기반 가중치)
    "aggregator_threads": {
        "outgoing_relations": 1.3,    # 서술적 풍부함으로 가장 높은 점수 → 높은 가중치
        "incoming_relations": 1.1,    # outgoing보다는 낮지만 관계 정보 중요
        "entity_properties": 1.2,     # 단편적이지만 정확한 정보 제공
        "connected_entities": 1.0,    # 2-hop 관계, 보조적 역할
        "type_and_summary": 1.15      # 타입/요약 정보는 컨텍스트 이해에 도움
    },

    # Entity Boost Mode
    "entity_boost_mode": "exact_match",  # 정확한 매칭 우선

    # 근거 선정 가중치
    "evidence_selection": {
        "top_k": 30,  # 상위 30개 근거 선택 (기본 15개에서 증가)
        "diversity_bonus": 0.1  # 다양한 스레드에서 온 근거에 보너스
    }
}


# =====================================================
# Paths
# =====================================================
RAGAS_DIR = Path(__file__).resolve().parent.parent  # backend/ragas
DATA_DIR = RAGAS_DIR / "data"
INTEGRATED_RESULTS_DIR = RAGAS_DIR / "fuseki" / "integrated_results"
INTEGRATED_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS_PATH = RAGAS_DIR / "questions.jsonl"


# =====================================================
# Utils
# =====================================================
def load_jsonl(path: Path) -> List[Dict]:
    """JSONL 파일 로드"""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def pick_question(item: dict) -> str:
    """질문 추출 (question_ko 우선)"""
    for k in ("question_ko", "question_en", "question"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def load_all_questions(items: List[Dict]) -> List[Dict]:
    """모든 질문 로드 (페르소나 필터링 없음)"""
    return items


def save_json(data: Any, path: Path):
    """JSON 저장"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# =====================================================
# Integrated Test Runner
# =====================================================
class IntegratedTestRunner:
    """
    통합 테스트 러너

    모든 기능을 활성화하고 커스텀 가중치를 적용하여 최적의 성능을 테스트합니다.
    """

    def __init__(
        self,
        questions_path: Path,
        output_dir: Path,
        limit: int = 0,
        debug: bool = False,
        custom_weights: Dict = None
    ):
        self.questions_path = questions_path
        self.output_dir = output_dir
        self.limit = limit
        self.debug = debug

        # 커스텀 가중치 (제공되지 않으면 최적화된 기본값 사용)
        self.weights = custom_weights if custom_weights else OPTIMIZED_WEIGHTS

        # RAGAS Metrics Loader 초기화
        self.ragas_loader = RagasMetricsLoader(debug=debug)
        self.ragas_loader.load_all()

        # 결과 저장
        self.result = None

        # 타임스탬프
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_questions(self) -> List[Dict]:
        """질문 로드 (모든 페르소나)"""
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_path}")

        items = load_jsonl(self.questions_path)

        if self.limit > 0:
            items = items[:self.limit]

        # 페르소나별 개수 출력
        persona_counts = {}
        for item in items:
            persona = item.get("persona_id", "unknown")
            persona_counts[persona] = persona_counts.get(persona, 0) + 1

        print(f"[INFO] Loaded {len(items)} questions total:")
        for persona, count in sorted(persona_counts.items()):
            print(f"  - {persona}: {count} questions")

        return items

    def create_integrated_test_config(self) -> Dict[str, Any]:
        """
        통합 테스트 설정 생성 (모든 기능 ON + 커스텀 가중치)

        Returns:
            GraphState.test_config 형식의 딕셔너리
        """
        semantic_weights = self.weights["semantic_expanders"]
        thread_weights = self.weights["aggregator_threads"]

        return {
            # 모든 Semantic Expander 활성화
            "semantic_expander": {
                "temporal": True,
                "category": True,
                "causal_chain": True,
                "pgvector": True
            },
            # 모든 Aggregator Thread 활성화
            "aggregator_threads": {
                "outgoing_relations": True,
                "incoming_relations": True,
                "entity_properties": True,
                "connected_entities": True,
                "type_and_summary": True
            },
            # Entity Boost Mode
            "entity_boost_mode": self.weights["entity_boost_mode"],

            # 커스텀 가중치 (GraphState에 전달)
            "custom_weights": {
                "semantic_expanders": semantic_weights,
                "aggregator_threads": thread_weights,
                "evidence_selection": self.weights["evidence_selection"]
            }
        }

    def run_test(self, questions: List[Dict]) -> Dict:
        """
        통합 테스트 실행

        Args:
            questions: 질문 리스트

        Returns:
            테스트 결과 딕셔너리
        """
        print(f"\n{'='*70}")
        print(f"[INTEGRATED TEST] All Features ON + Custom Weights")
        print(f"{'='*70}")
        print(f"  Semantic Expanders: ALL ON (weights: {self.weights['semantic_expanders']})")
        print(f"  Aggregator Threads: ALL ON (weights: {self.weights['aggregator_threads']})")
        print(f"  Entity Boost Mode: {self.weights['entity_boost_mode']}")
        print(f"  Questions: {len(questions)}")
        print()

        # 그래프 생성
        graph = create_graph_flow()

        # 샘플 수집
        samples = []
        raw_logs = []

        for idx, item in enumerate(questions, start=1):
            question = pick_question(item)
            if not question:
                continue

            persona = item.get("persona_id", "unknown")
            print(f"\n  [{idx}/{len(questions)}] ({persona}) Q: {question[:60]}...")

            try:
                # 통합 테스트 설정
                test_config = self.create_integrated_test_config()

                # 초기 상태 생성
                initial_state: GraphState = {
                    "query": question,
                    "extracted_entities": [],
                    "executed_nodes": [],
                    "thread_weights": self.weights["aggregator_threads"],  # 가중치 직접 전달
                    "node_execution_times": {},
                    "is_historical": True,
                    "test_config": test_config
                }

                # 그래프 실행
                start_time = time.time()
                final_state = graph.invoke(initial_state)
                elapsed = time.time() - start_time

                # 결과 추출
                answer = final_state.get("final_answer", "")
                evidences = final_state.get("evidences", [])
                contexts = extract_contexts_from_evidences(evidences)

                # 토큰 사용량 추출
                total_tokens = final_state.get("total_tokens", 0)
                prompt_tokens = final_state.get("prompt_tokens", 0)
                completion_tokens = final_state.get("completion_tokens", 0)

                # 샘플 생성
                sample = self.ragas_loader.create_sample(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                    reference=item.get("reference")
                )
                samples.append(sample)

                # 로그 기록
                raw_logs.append({
                    "idx": idx,
                    "persona": persona,
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                    "n_contexts": len(contexts),
                    "elapsed_seconds": elapsed,
                    "tokens": {
                        "total": total_tokens,
                        "prompt": prompt_tokens,
                        "completion": completion_tokens
                    },
                    "thread_evidence_counts": self._count_evidences_by_thread(evidences)
                })

                print(f"      ✓ Answer: {answer[:80]}...")
                print(f"      ✓ Contexts: {len(contexts)}")
                print(f"      ✓ Time: {elapsed:.2f}s, Tokens: {total_tokens}")

            except Exception as e:
                print(f"      ✗ Error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                raw_logs.append({
                    "idx": idx,
                    "persona": persona,
                    "question": question,
                    "error": repr(e)
                })

        # RAGAS 평가
        print(f"\n  [RAGAS Evaluation]")
        scores = {}
        if samples:
            try:
                scores = evaluate_with_ragas(
                    self.ragas_loader,
                    samples,
                    debug=self.debug
                )
                print(f"    Scores: {scores}")
            except Exception as e:
                print(f"    ✗ RAGAS evaluation failed: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()

        # 결과 정리
        result = {
            "test_type": "integrated",
            "config": {
                "all_semantic_expanders_on": True,
                "all_aggregator_threads_on": True,
                "entity_boost_mode": self.weights["entity_boost_mode"],
                "custom_weights": self.weights
            },
            "n_questions": len(questions),
            "n_samples": len(samples),
            "scores": scores,
            "raw_logs": raw_logs,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def _count_evidences_by_thread(self, evidences: List[Dict]) -> Dict[str, int]:
        """스레드별 근거 개수 집계"""
        counts = {}
        for ev in evidences:
            ev_type = ev.get("type", "unknown")
            counts[ev_type] = counts.get(ev_type, 0) + 1
        return counts

    def run_all_tests(self):
        """모든 테스트 실행 (40개 질문 한번에)"""
        questions = self.load_questions()

        # 모든 질문을 한번에 테스트
        self.result = self.run_test(questions)

        # 결과 저장
        self.save_results()

        # 요약 출력
        self.print_summary()

    def save_results(self):
        """결과 저장"""
        # 전체 결과 저장 (raw logs 포함)
        results_path = self.output_dir / f"integrated_results_all_{self.timestamp}_raw.json"
        save_json(self.result, results_path)
        print(f"\n[SAVE] Results saved: {results_path}")

        # 간소화된 결과 저장 (raw logs 제외)
        simplified = {k: v for k, v in self.result.items() if k != "raw_logs"}

        # 기본 통계 추가
        if self.result.get("raw_logs"):
            raw_logs = self.result["raw_logs"]
            simplified["avg_contexts"] = sum(
                log.get("n_contexts", 0) for log in raw_logs
            ) / len(raw_logs) if raw_logs else 0
            simplified["avg_elapsed"] = sum(
                log.get("elapsed_seconds", 0) for log in raw_logs
            ) / len(raw_logs) if raw_logs else 0

            # 페르소나별 통계
            persona_stats = {}
            for log in raw_logs:
                persona = log.get("persona", "unknown")
                if persona not in persona_stats:
                    persona_stats[persona] = {"count": 0, "contexts": []}
                persona_stats[persona]["count"] += 1
                persona_stats[persona]["contexts"].append(log.get("n_contexts", 0))

            simplified["persona_stats"] = {
                p: {
                    "count": stats["count"],
                    "avg_contexts": sum(stats["contexts"]) / len(stats["contexts"]) if stats["contexts"] else 0
                }
                for p, stats in persona_stats.items()
            }

        simplified_path = self.output_dir / f"integrated_results_all_{self.timestamp}.json"
        save_json(simplified, simplified_path)
        print(f"[SAVE] Simplified results saved: {simplified_path}")

    def print_summary(self):
        """결과 요약 출력"""
        print(f"\n{'='*70}")
        print("Integrated Test Summary")
        print(f"{'='*70}")

        n_samples = self.result.get("n_samples", 0)
        scores = self.result.get("scores", {})

        print(f"\nTotal Samples: {n_samples}")

        # 페르소나별 통계 (raw_logs에서 집계)
        if self.result.get("raw_logs"):
            persona_counts = {}
            for log in self.result["raw_logs"]:
                persona = log.get("persona", "unknown")
                persona_counts[persona] = persona_counts.get(persona, 0) + 1

            print("\nPersona Distribution:")
            for persona, count in sorted(persona_counts.items()):
                print(f"  - {persona}: {count} questions")

        # RAGAS 점수
        if scores:
            print("\nRAGAS Scores:")
            for metric, score in scores.items():
                print(f"  - {metric}: {score:.4f}")
        else:
            print("\n  - No scores available")


# =====================================================
# Main
# =====================================================
def main():
    parser = argparse.ArgumentParser(
        description="Integrated Test Runner for Fuseki RAG System (All Features ON + Custom Weights)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of questions (0 = no limit, default: 0)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # 테스트 러너 생성
    runner = IntegratedTestRunner(
        questions_path=QUESTIONS_PATH,
        output_dir=INTEGRATED_RESULTS_DIR,
        limit=args.limit,
        debug=args.debug
    )

    # 테스트 실행
    runner.run_all_tests()

    print("\n[DONE] Integrated test completed!")


if __name__ == "__main__":
    main()
