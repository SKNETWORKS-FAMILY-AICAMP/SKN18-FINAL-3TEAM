"""
Ablation 실험 결과 분석 도구
"""

from typing import Dict, List, Any
import json
from pathlib import Path
import pandas as pd


class ResultAnalyzer:
    """실험 결과 분석기"""

    def __init__(self, result_file: str):
        """
        Args:
            result_file: 실험 결과 JSON 파일 경로
        """
        self.result_file = Path(result_file)
        self.results = self._load_results()

    def _load_results(self) -> List[Dict[str, Any]]:
        """결과 파일 로드"""
        with open(self.result_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def calculate_metric_averages(self) -> pd.DataFrame:
        """실험 설정별 메트릭 평균 계산

        Returns:
            실험별 평균 점수 DataFrame
        """
        experiment_scores = {}

        for result in self.results:
            exp_name = result["experiment_name"]
            metrics = result.get("metrics", {})

            if exp_name not in experiment_scores:
                experiment_scores[exp_name] = {
                    "intent_preservation": [],
                    "relation_coherence": [],
                    "terminal_triple_validity": [],
                    "evidence_diversity": [],
                    "convergence_utilization": []
                }

            # 각 메트릭 점수 수집
            if "intent_preservation" in metrics:
                experiment_scores[exp_name]["intent_preservation"].append(
                    metrics["intent_preservation"]["score"]
                )

            if "relation_coherence" in metrics:
                experiment_scores[exp_name]["relation_coherence"].append(
                    metrics["relation_coherence"]["score"]
                )

            if "terminal_triple_validity" in metrics:
                experiment_scores[exp_name]["terminal_triple_validity"].append(
                    metrics["terminal_triple_validity"]["score"]
                )

            if "evidence_diversity" in metrics:
                experiment_scores[exp_name]["evidence_diversity"].append(
                    metrics["evidence_diversity"]["score"]
                )

            if "convergence_utilization" in metrics:
                experiment_scores[exp_name]["convergence_utilization"].append(
                    metrics["convergence_utilization"]["score"]
                )

        # 평균 계산
        avg_scores = {}
        for exp_name, scores in experiment_scores.items():
            avg_scores[exp_name] = {
                metric: sum(values) / len(values) if values else 0.0
                for metric, values in scores.items()
            }

        # DataFrame 변환
        df = pd.DataFrame(avg_scores).T
        return df

    def compare_to_baseline(self, baseline_name: str) -> pd.DataFrame:
        """Baseline 대비 성능 비교

        Args:
            baseline_name: Baseline 실험 이름

        Returns:
            Baseline 대비 점수 차이 DataFrame
        """
        avg_df = self.calculate_metric_averages()

        if baseline_name not in avg_df.index:
            raise ValueError(f"Baseline '{baseline_name}' not found in results")

        baseline_scores = avg_df.loc[baseline_name]

        # Baseline 대비 차이 계산
        diff_df = avg_df - baseline_scores

        return diff_df

    def generate_report(self, output_file: str = None):
        """분석 리포트 생성

        Args:
            output_file: 리포트 저장 경로 (None이면 콘솔 출력)
        """
        report_lines = []

        report_lines.append("=" * 70)
        report_lines.append("Ablation Study 결과 분석")
        report_lines.append("=" * 70)
        report_lines.append("")

        # 1. 전체 실험 개수
        report_lines.append(f"총 실험 개수: {len(self.results)}")
        report_lines.append("")

        # 2. 실험별 평균 점수
        avg_df = self.calculate_metric_averages()
        report_lines.append("실험별 평균 점수:")
        report_lines.append(avg_df.to_string())
        report_lines.append("")

        # 3. Baseline 대비 비교 (semantic_expander_baseline)
        if "semantic_expander_baseline" in avg_df.index:
            report_lines.append("Semantic Expander Baseline 대비:")
            diff_df = self.compare_to_baseline("semantic_expander_baseline")
            report_lines.append(diff_df.to_string())
            report_lines.append("")

        # 4. Thread Baseline 대비 비교
        if "thread_baseline" in avg_df.index:
            report_lines.append("Thread Baseline 대비:")
            diff_df = self.compare_to_baseline("thread_baseline")
            report_lines.append(diff_df.to_string())
            report_lines.append("")

        # 5. 최고 성능 실험 찾기
        report_lines.append("메트릭별 최고 성능 실험:")
        for metric in avg_df.columns:
            best_exp = avg_df[metric].idxmax()
            best_score = avg_df[metric].max()
            report_lines.append(f"  - {metric}: {best_exp} ({best_score:.3f})")
        report_lines.append("")

        report = "\n".join(report_lines)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"리포트 저장: {output_path}")
        else:
            print(report)


if __name__ == "__main__":
    # 사용 예시
    analyzer = ResultAnalyzer("data/results/semantic_expander_ablation.json")
    analyzer.generate_report()
