"""
Automated Test Runner for Fuseki RAG System

20가지 조합을 자동으로 테스트하고 RAGAS 평가를 수행합니다.

Usage:
    python automated_test_runner.py --limit 5 --debug
    python automated_test_runner.py --persona foreigner_culture_history --save-every 2
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
from backend.ragas.fuseki.config_manager import ConfigManager
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


def filter_questions_by_persona(items: List[Dict], persona_id: str) -> List[Dict]:
    """Persona ID로 질문 필터링"""
    return [item for item in items if item.get("persona_id") == persona_id]


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

    20가지 조합을 순차적으로 테스트하고 RAGAS 평가를 수행합니다.
    """

    def __init__(
        self,
        questions_path: Path,
        output_dir: Path,
        persona_id: str = "foreigner_culture_history",
        limit: int = 0,
        debug: bool = False,
        save_every: int = 5
    ):
        self.questions_path = questions_path
        self.output_dir = output_dir
        self.persona_id = persona_id
        self.limit = limit
        self.debug = debug
        self.save_every = save_every

        # Config Manager 초기화
        self.config_manager = ConfigManager()
        self.configs = self.config_manager.generate_all_configs()

        # RAGAS Metrics Loader 초기화
        self.ragas_loader = RagasMetricsLoader(debug=debug)
        self.ragas_loader.load_all()

        # 결과 저장
        self.all_results = []

        # 타임스탬프
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_questions(self) -> List[Dict]:
        """질문 로드 및 필터링"""
        if not self.questions_path.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_path}")

        items = load_jsonl(self.questions_path)

        # Persona 필터링
        items = filter_questions_by_persona(items, self.persona_id)

        if self.limit > 0:
            items = items[:self.limit]

        print(f"[INFO] Loaded {len(items)} questions (persona: {self.persona_id})")
        return items

    def run_single_test(
        self,
        config: Dict,
        questions: List[Dict]
    ) -> Dict:
        """
        단일 조합 테스트 실행

        Args:
            config: 노드 설정
            questions: 질문 리스트

        Returns:
            테스트 결과 딕셔너리
        """
        test_id = config["test_id"]
        combination_id = config["combination_id"]

        print(f"\n{'='*70}")
        print(f"[TEST {test_id}/20] {config['description']}")
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
                    "is_history_related": True  # history_check_node를 스킵하기 위해
                }

                # 설정 적용
                initial_state = self.config_manager.apply_config_to_state(
                    initial_state,
                    config
                )

                # 그래프 실행
                start_time = time.time()
                final_state = graph.invoke(initial_state)
                elapsed = time.time() - start_time

                # 결과 추출
                answer = final_state.get("answer", "")
                evidences = final_state.get("evidences", [])
                contexts = extract_contexts_from_evidences(evidences)

                # 토큰 사용량 추출 (final_state에서)
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

        # 결과 정리
        result = {
            "test_id": test_id,
            "combination_id": combination_id,
            "config": config,
            "n_questions": len(questions),
            "n_samples": len(samples),
            "scores": scores,
            "raw_logs": raw_logs,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def run_all_tests(self):
        """모든 20가지 조합 테스트 실행"""
        questions = self.load_questions()

        print(f"\n{'='*70}")
        print(f"Starting Automated Tests")
        print(f"{'='*70}")
        print(f"  - Total Combinations: {len(self.configs)}")
        print(f"  - Questions per Test: {len(questions)}")
        print(f"  - Persona: {self.persona_id}")
        print(f"  - Output: {self.output_dir}")
        print()

        for config in self.configs:
            result = self.run_single_test(config, questions)
            self.all_results.append(result)

            # 중간 저장
            if config["test_id"] % self.save_every == 0:
                self.save_results()

        # 최종 저장
        self.save_results()

        # 요약 출력
        self.print_summary()

    def save_results(self):
        """결과 저장"""
        # 전체 결과 저장
        results_path = self.output_dir / f"all_results_{self.timestamp}.json"
        save_json(self.all_results, results_path)
        print(f"\n[CHECKPOINT] Results saved: {results_path}")

        # 점수 요약 저장
        summary_path = self.output_dir / f"summary_{self.timestamp}.json"
        summary = self.generate_summary()
        save_json(summary, summary_path)
        print(f"[CHECKPOINT] Summary saved: {summary_path}")

    def generate_summary(self) -> Dict:
        """결과 요약 생성"""
        summary = {
            "timestamp": self.timestamp,
            "persona_id": self.persona_id,
            "n_tests": len(self.all_results),
            "test_results": []
        }

        for result in self.all_results:
            summary["test_results"].append({
                "test_id": result["test_id"],
                "combination_id": result["combination_id"],
                "semantic_expander": result["config"]["semantic_expander"]["active_type"],
                "aggregator": result["config"]["aggregator"]["active_type"],
                "n_samples": result["n_samples"],
                "scores": result["scores"]
            })

        return summary

    def print_summary(self):
        """결과 요약 출력"""
        print(f"\n{'='*70}")
        print("Test Summary")
        print(f"{'='*70}")

        for result in self.all_results:
            test_id = result["test_id"]
            combination_id = result["combination_id"]
            scores = result["scores"]

            print(f"\n[{test_id}/20] {combination_id}")
            if scores:
                for metric, score in scores.items():
                    print(f"  - {metric}: {score:.4f}")
            else:
                print("  - No scores available")


# =====================================================
# Main
# =====================================================
def main():
    parser = argparse.ArgumentParser(
        description="Automated Test Runner for Fuseki RAG System"
    )
    parser.add_argument(
        "--persona",
        type=str,
        default="foreigner_culture_history",
        help="Persona ID to test (default: foreigner_culture_history)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of questions per test (0 = no limit)"
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
        help="Save results every N tests (default: 5)"
    )

    args = parser.parse_args()

    # 테스트 러너 생성
    runner = AutomatedTestRunner(
        questions_path=QUESTIONS_PATH,
        output_dir=FUSEKI_RESULTS_DIR,
        persona_id=args.persona,
        limit=args.limit,
        debug=args.debug,
        save_every=args.save_every
    )

    # 모든 테스트 실행
    runner.run_all_tests()

    print("\n[DONE] All tests completed!")


if __name__ == "__main__":
    main()
