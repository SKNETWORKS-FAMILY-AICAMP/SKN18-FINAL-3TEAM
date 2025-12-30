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

# Token tracking
from backend.ragas.fuseki.token_tracker import track_tokens_from_events


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
        boost_filter: str = None,
        worker_id: int = None,
        num_workers: int = None
    ):
        self.questions_path = questions_path
        self.output_dir = output_dir
        self.limit = limit
        self.debug = debug
        self.save_every = save_every
        self.worker_id = worker_id
        self.num_workers = num_workers

        # Config Manager 초기화
        self.config_manager = ConfigurationManager()

        # 필터링된 조합 가져오기
        if semantic_filter or thread_filter or boost_filter:
            all_combinations = self.config_manager.get_combinations_by_filters(
                semantic=semantic_filter,
                thread=thread_filter,
                boost=boost_filter
            )
        else:
            all_combinations = self.config_manager.get_all_combinations()

        # 워커별 조합 분할
        if worker_id is not None and num_workers is not None:
            # 조합을 워커 수만큼 분할
            chunk_size = len(all_combinations) // num_workers
            start_idx = worker_id * chunk_size
            if worker_id == num_workers - 1:
                # 마지막 워커는 나머지 모두 처리
                end_idx = len(all_combinations)
            else:
                end_idx = start_idx + chunk_size
            self.combinations = all_combinations[start_idx:end_idx]
            print(f"[WORKER {worker_id}] Processing combinations {start_idx} to {end_idx-1} ({len(self.combinations)} combinations)")
        else:
            self.combinations = all_combinations

        # RAGAS Metrics Loader 초기화
        self.ragas_loader = RagasMetricsLoader(debug=debug)
        self.ragas_loader.load_all()

        # 결과 저장
        self.all_results = []

        # 타임스탬프
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 워커 ID가 있으면 타임스탬프에 포함
        if worker_id is not None:
            self.timestamp = f"{self.timestamp}_worker{worker_id}"

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

                # 그래프 실행 및 토큰 추적
                start_time = time.time()
                try:
                    # 이벤트 스트리밍으로 토큰 추적 시도
                    final_state, token_usage = track_tokens_from_events(graph, initial_state)
                except Exception as e:
                    # 실패 시 일반 invoke 사용
                    print(f"      Warning: Token tracking failed ({e}), using regular invoke")
                    final_state = graph.invoke(initial_state)
                    token_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
                
                elapsed = time.time() - start_time

                # 결과 추출
                answer = final_state.get("final_answer", "")
                evidences = final_state.get("evidences", [])
                contexts = extract_contexts_from_evidences(evidences)

                # 토큰 사용량 추출
                total_tokens = token_usage.get("total_tokens", 0)
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)

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
        individual_scores = []
        if samples:
            try:
                # 개별 점수도 함께 반환받기 위해 return_individual=True 사용
                evaluation_result = evaluate_with_ragas(
                    self.ragas_loader,
                    samples,
                    debug=self.debug,
                    return_individual=True
                )
                
                # 평균 점수
                if isinstance(evaluation_result, dict) and "average_scores" in evaluation_result:
                    scores = evaluation_result["average_scores"]
                    individual_scores = evaluation_result.get("individual_scores", [])
                else:
                    # 이전 형식 호환 (평균만 반환하는 경우)
                    scores = evaluation_result
                    individual_scores = []
                
                print(f"    Scores: {scores}")
            except Exception as e:
                print(f"    ✗ RAGAS evaluation failed: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()

        # raw_logs에 개별 RAGAS 점수 추가
        for i, log in enumerate(raw_logs):
            if i < len(individual_scores) and individual_scores[i]:
                log["ragas_scores"] = individual_scores[i]
            else:
                # 개별 점수가 없으면 평균 점수 추가
                log["ragas_scores"] = scores

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
        if self.worker_id is not None:
            print(f"  - Worker ID: {self.worker_id}/{self.num_workers}")
        print(f"  - Output: {self.output_dir}")
        print()

        for idx, test_config in enumerate(self.combinations, start=1):
            result = self.run_single_test(test_config, questions)
            self.all_results.append(result)

            # 중간 저장 (워커별 인덱스 기반)
            if idx % self.save_every == 0:
                self.save_results()

        # 최종 저장
        self.save_results()

        # 요약 출력
        self.print_summary()

    def save_results(self):
        """결과 저장 (상세 파일 하나만 저장)"""
        n_combos = len(self.combinations)
        
        # 워커 ID가 있으면 파일명에 포함
        worker_suffix = f"_worker{self.worker_id}" if self.worker_id is not None else ""

        # 전체 결과 저장 (raw logs 포함) - 상세 파일 하나만 저장
        results_path = self.output_dir / f"ragas_results_{n_combos}combos_{self.timestamp}_raw{worker_suffix}.json"
        save_json(self.all_results, results_path)
        print(f"\n[CHECKPOINT] Results saved: {results_path}")


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
    parser.add_argument(
        "--worker-id",
        type=int,
        default=None,
        help="Worker ID for parallel processing (0-based, e.g., 0-7 for 8 workers)"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=None,
        help="Total number of workers for parallel processing (e.g., 8)"
    )

    args = parser.parse_args()

    # 워커 인자 검증
    if (args.worker_id is not None) != (args.num_workers is not None):
        parser.error("--worker-id and --num-workers must be specified together")

    if args.worker_id is not None:
        if args.worker_id < 0 or args.worker_id >= args.num_workers:
            parser.error(f"--worker-id must be between 0 and {args.num_workers - 1}")

    # 테스트 러너 생성
    runner = AutomatedTestRunner(
        questions_path=QUESTIONS_PATH,
        output_dir=FUSEKI_RESULTS_DIR,
        limit=args.limit,
        debug=args.debug,
        save_every=args.save_every,
        semantic_filter=args.semantic,
        thread_filter=args.thread,
        boost_filter=args.boost,
        worker_id=args.worker_id,
        num_workers=args.num_workers
    )

    # 모든 테스트 실행
    runner.run_all_tests()

    print("\n[DONE] All tests completed!")


if __name__ == "__main__":
    main()
