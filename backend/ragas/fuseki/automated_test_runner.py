"""
Automated Test Runner for Fuseki RAG System

80가지 조합을 자동으로 테스트하고 RAGAS 평가를 수행합니다.
- 4가지 Semantic Expander × 5가지 Aggregator Thread × 4가지 Entity Boost Mode = 80가지

Usage:
    # 모든 질문(40개)으로 80가지 조합 테스트 (기본값)
    python backend/ragas/fuseki/automated_test_runner.py --save-every 10

    # 각 조합당 3개 질문만 테스트 (디버깅용)
    python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug

    # 특정 조합만 테스트
    python backend/ragas/fuseki/automated_test_runner.py --semantic temporal --thread outgoing_relations --boost exact_match --limit 3
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
from backend.ragas.fuseki.config_manager import (
    ConfigurationManager,
    TestConfiguration,
    validate_test_config
)
from backend.ragas.fuseki.ragas_metrics import (
    RagasMetricsLoader,
    extract_contexts_from_evidences,
    evaluate_with_ragas
)

# Langgraph imports
from backend.langgraph_fuseki.graph import create_graph_flow
from backend.langgraph_fuseki.state import GraphState


# =====================================================
# Paths
# =====================================================
RAGAS_DIR = Path(__file__).resolve().parent.parent  # backend/ragas
DATA_DIR = RAGAS_DIR / "data"
FUSEKI_RESULTS_DIR = RAGAS_DIR / "fuseki" / "results"
FUSEKI_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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


def load_all_questions_with_stats(items: List[Dict]) -> tuple:
    """모든 질문 로드 및 통계 반환"""
    persona_counts = {}
    for item in items:
        persona = item.get("persona_id", "unknown")
        persona_counts[persona] = persona_counts.get(persona, 0) + 1
    return items, persona_counts


def save_json(data: Any, path: Path):
    """JSON 저장"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# =====================================================
# Test Runner
# =====================================================
class AutomatedTestRunner:
    """
    자동화 테스트 러너

    80가지 조합을 순차적으로 테스트하고 RAGAS 평가를 수행합니다.
    - 4가지 Semantic Expander × 5가지 Aggregator Thread × 4가지 Entity Boost Mode = 80가지
    """

    def __init__(
        self,
        questions_path: Path,
        output_dir: Path,
        limit: int = 0,
        debug: bool = False,
        save_every: int = 10,
        semantic_filter: str = None,
        thread_filter: str = None,
        boost_filter: str = None
    ):
        self.questions_path = questions_path
        self.output_dir = output_dir
        self.limit = limit
        self.debug = debug
        self.save_every = save_every

        # Config Manager 초기화
        self.config_manager = ConfigurationManager()

        # 필터링된 조합 가져오기
        if semantic_filter or thread_filter or boost_filter:
            self.combinations = self.config_manager.get_combinations_by_filters(
                semantic=semantic_filter,
                thread=thread_filter,
                boost=boost_filter
            )
        else:
            self.combinations = self.config_manager.get_all_combinations()

        # RAGAS Metrics Loader 초기화
        self.ragas_loader = RagasMetricsLoader(debug=debug)
        self.ragas_loader.load_all()

        # 결과 저장
        self.all_results = []

        # 타임스탬프
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_questions(self) -> List[Dict]:
        """질문 로드 (모든 페르소나)"""
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_path}")

        items = load_jsonl(self.questions_path)

        if self.limit > 0:
            items = items[:self.limit]

        # 페르소나별 통계 출력
        items, persona_counts = load_all_questions_with_stats(items)
        print(f"[INFO] Loaded {len(items)} questions total:")
        for persona, count in sorted(persona_counts.items()):
            print(f"  - {persona}: {count} questions")

        return items

    def run_single_test(
        self,
        test_config: TestConfiguration,
        questions: List[Dict]
    ) -> Dict:
        """
        단일 조합 테스트 실행

        Args:
            test_config: TestConfiguration 객체
            questions: 질문 리스트

        Returns:
            테스트 결과 딕셔너리
        """
        combination_id = test_config.combination_id
        description = test_config.get_description()

        print(f"\n{'='*70}")
        print(f"[TEST {combination_id}/80] {description}")
        print(f"{'='*70}")

        # 그래프 생성
        graph = create_graph_flow()

        # 샘플 수집
        samples = []
        raw_logs = []

        for idx, item in enumerate(questions, start=1):
            question = pick_question(item)
            if not question:
                continue

            print(f"\n  [{idx}/{len(questions)}] Q: {question[:60]}...")

            try:
                # 초기 상태 생성
                initial_state: GraphState = {
                    "query": question,
                    "extracted_entities": [],
                    "executed_nodes": [],
                    "thread_weights": {},
                    "node_execution_times": {},
                    "is_historical": True,  # 역사 관련 질문으로 간주
                    "test_config": test_config.to_test_config()  # test_config 주입
                }

                # 그래프 실행
                start_time = time.time()
                final_state = graph.invoke(initial_state)
                elapsed = time.time() - start_time

                # 결과 추출
                answer = final_state.get("final_answer", "")
                evidences = final_state.get("evidences", [])
                contexts = extract_contexts_from_evidences(evidences)

                # 토큰 사용량 추출 (final_state에서)
                # TODO: LLM 호출 시 토큰 사용량 추적 필요
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

                # 로그 기록 (확장된 정보 포함)
                raw_logs.append({
                    "idx": idx,
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,  # 전체 컨텍스트 저장
                    "n_contexts": len(contexts),
                    "elapsed_seconds": elapsed,
                    "tokens": {
                        "total": total_tokens,
                        "prompt": prompt_tokens,
                        "completion": completion_tokens
                    }
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
            "combination_id": combination_id,
            "semantic_expander": test_config.semantic_expander,
            "aggregator_thread": test_config.aggregator_thread,
            "entity_boost_mode": test_config.entity_boost_mode,
            "short_name": test_config.get_short_name(),
            "n_questions": len(questions),
            "n_samples": len(samples),
            "scores": scores,
            "raw_logs": raw_logs,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def run_all_tests(self):
        """모든 조합 테스트 실행 (최대 80가지)"""
        questions = self.load_questions()

        print(f"\n{'='*70}")
        print(f"Starting Automated Tests")
        print(f"{'='*70}")
        print(f"  - Total Combinations: {len(self.combinations)}")
        print(f"  - Questions per Test: {len(questions)}")
        print(f"  - Persona: {self.persona_id}")
        print(f"  - Output: {self.output_dir}")
        print()

        for test_config in self.combinations:
            result = self.run_single_test(test_config, questions)
            self.all_results.append(result)

            # 중간 저장
            if test_config.combination_id % self.save_every == 0:
                self.save_results()

        # 최종 저장
        self.save_results()

        # 요약 출력
        self.print_summary()

    def save_results(self):
        """결과 저장"""
        n_combos = len(self.combinations)

        # 전체 결과 저장 (raw logs 포함)
        results_path = self.output_dir / f"ragas_results_{n_combos}combos_{self.timestamp}_raw.json"
        save_json(self.all_results, results_path)
        print(f"\n[CHECKPOINT] Results saved: {results_path}")

        # 점수 요약 저장
        summary_path = self.output_dir / f"ragas_summary_{n_combos}combos_{self.timestamp}.json"
        summary = self.generate_summary()
        save_json(summary, summary_path)
        print(f"[CHECKPOINT] Summary saved: {summary_path}")

        # 간소화된 결과 저장 (raw logs 제외)
        simplified_results = []
        for result in self.all_results:
            simplified = {k: v for k, v in result.items() if k != "raw_logs"}
            simplified_results.append(simplified)

        simplified_path = self.output_dir / f"ragas_results_{n_combos}combos_{self.timestamp}.json"
        save_json(simplified_results, simplified_path)
        print(f"[CHECKPOINT] Simplified results saved: {simplified_path}")

    def generate_summary(self) -> Dict:
        """결과 요약 생성"""
        summary = {
            "timestamp": self.timestamp,
            "persona_id": self.persona_id,
            "n_combinations": len(self.all_results),
            "test_results": []
        }

        for result in self.all_results:
            summary["test_results"].append({
                "combination_id": result["combination_id"],
                "semantic_expander": result["semantic_expander"],
                "aggregator_thread": result["aggregator_thread"],
                "entity_boost_mode": result["entity_boost_mode"],
                "short_name": result["short_name"],
                "n_samples": result["n_samples"],
                "scores": result["scores"]
            })

        return summary

    def print_summary(self):
        """결과 요약 출력"""
        print(f"\n{'='*70}")
        print("Test Summary")
        print(f"{'='*70}")

        n_combos = len(self.combinations)

        for result in self.all_results:
            combination_id = result["combination_id"]
            short_name = result["short_name"]
            scores = result["scores"]

            print(f"\n[{combination_id}/{n_combos}] {short_name}")
            if scores:
                for metric, score in scores.items():
                    print(f"  - {metric}: {score:.4f}")
            else:
                print("  - No scores available")

        # 평균 점수 계산 및 출력
        print(f"\n{'='*70}")
        print("Average Scores")
        print(f"{'='*70}")

        all_scores = {}
        for result in self.all_results:
            for metric, score in result.get("scores", {}).items():
                if metric not in all_scores:
                    all_scores[metric] = []
                all_scores[metric].append(score)

        for metric, scores_list in all_scores.items():
            avg_score = sum(scores_list) / len(scores_list) if scores_list else 0
            print(f"  - {metric}: {avg_score:.4f} (n={len(scores_list)})")


# =====================================================
# Main
# =====================================================
def main():
    parser = argparse.ArgumentParser(
        description="Automated Test Runner for Fuseki RAG System (80 Combinations with 40 Questions)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of questions per combination (0 = all 40 questions, default: 0)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=5,
        help="Save results every N combinations (default: 5)"
    )
    parser.add_argument(
        "--semantic",
        type=str,
        default=None,
        help="Filter by semantic expander: temporal, category, causal_chain, pgvector"
    )
    parser.add_argument(
        "--thread",
        type=str,
        default=None,
        help="Filter by aggregator thread: outgoing_relations, incoming_relations, entity_properties, connected_entities, type_and_summary"
    )
    parser.add_argument(
        "--boost",
        type=str,
        default=None,
        help="Filter by entity boost mode: exact_match, partial_match, normalized_match, penalty_match"
    )

    args = parser.parse_args()

    # 테스트 러너 생성
    runner = AutomatedTestRunner(
        questions_path=QUESTIONS_PATH,
        output_dir=FUSEKI_RESULTS_DIR,
        limit=args.limit,
        debug=args.debug,
        save_every=args.save_every,
        semantic_filter=args.semantic,
        thread_filter=args.thread,
        boost_filter=args.boost
    )

    # 모든 테스트 실행
    runner.run_all_tests()

    print("\n[DONE] All tests completed!")


if __name__ == "__main__":
    main()
