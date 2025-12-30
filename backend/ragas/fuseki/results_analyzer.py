"""
Results Analyzer and Reporter

20가지 조합의 테스트 결과를 분석하고 리포트를 생성합니다.

Usage:
    python results_analyzer.py --input results/all_results_20250101_120000.json
    python results_analyzer.py --input results/all_results_20250101_120000.json --export-csv
"""

import sys
from pathlib import Path

# ===== PROJECT ROOT 설정 =====
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import argparse
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime


# =====================================================
# Paths
# =====================================================
FUSEKI_RESULTS_DIR = Path(__file__).resolve().parent / "results"


# =====================================================
# Results Analyzer
# =====================================================
class ResultsAnalyzer:
    """
    결과 분석기

    20가지 조합의 테스트 결과를 분석하고 순위를 매깁니다.
    """

    def __init__(self, results_path: Path):
        self.results_path = results_path
        self.results = self.load_results()
        self.df = None

    def load_results(self) -> List[Dict]:
        """결과 파일 로드"""
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_path}")

        with self.results_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def create_dataframe(self) -> pd.DataFrame:
        """결과를 DataFrame으로 변환"""
        rows = []

        for result in self.results:
            test_id = result["test_id"]
            combination_id = result["combination_id"]
            config = result["config"]
            scores = result["scores"]

            row = {
                "test_id": test_id,
                "combination_id": combination_id,
                "semantic_expander": config["semantic_expander"]["active_type"],
                "aggregator": config["aggregator"]["active_type"],
                "n_samples": result["n_samples"]
            }

            # 점수 추가
            for metric, score in scores.items():
                row[metric] = score

            rows.append(row)

        self.df = pd.DataFrame(rows)
        return self.df

    def calculate_rankings(self) -> pd.DataFrame:
        """
        각 메트릭별 순위 계산

        Returns:
            순위가 추가된 DataFrame
        """
        if self.df is None:
            self.create_dataframe()

        df_ranked = self.df.copy()

        # 메트릭 컬럼 추출
        metric_cols = [col for col in df_ranked.columns
                       if col not in ["test_id", "combination_id", "semantic_expander",
                                      "aggregator", "n_samples"]]

        # 각 메트릭별 순위 계산 (높을수록 좋음)
        for metric in metric_cols:
            df_ranked[f"{metric}_rank"] = df_ranked[metric].rank(
                ascending=False,
                method="min"
            )

        # 평균 순위 계산
        rank_cols = [f"{metric}_rank" for metric in metric_cols]
        if rank_cols:
            df_ranked["avg_rank"] = df_ranked[rank_cols].mean(axis=1)
            df_ranked["overall_rank"] = df_ranked["avg_rank"].rank(method="min")

        # 순위로 정렬
        if "overall_rank" in df_ranked.columns:
            df_ranked = df_ranked.sort_values("overall_rank")

        return df_ranked

    def get_top_k_combinations(self, k: int = 5) -> pd.DataFrame:
        """
        상위 K개 조합 반환

        Args:
            k: 상위 K개

        Returns:
            상위 K개 조합
        """
        df_ranked = self.calculate_rankings()
        return df_ranked.head(k)

    def get_metric_winners(self) -> Dict[str, Dict]:
        """
        각 메트릭별 1위 조합 반환

        Returns:
            {metric_name: {combination_id, score, ...}}
        """
        if self.df is None:
            self.create_dataframe()

        metric_cols = [col for col in self.df.columns
                       if col not in ["test_id", "combination_id", "semantic_expander",
                                      "aggregator", "n_samples"]]

        winners = {}
        for metric in metric_cols:
            idx = self.df[metric].idxmax()
            winner = self.df.loc[idx].to_dict()
            winners[metric] = winner

        return winners

    def generate_report(self) -> str:
        """
        분석 리포트 생성

        Returns:
            리포트 문자열
        """
        df_ranked = self.calculate_rankings()
        top_5 = self.get_top_k_combinations(5)
        metric_winners = self.get_metric_winners()

        report = []
        report.append("="*70)
        report.append("RAGAS Evaluation Results - Analysis Report")
        report.append("="*70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {len(self.results)}")
        report.append("")

        # 전체 순위
        report.append("-"*70)
        report.append("Overall Rankings (Top 5)")
        report.append("-"*70)
        for idx, row in top_5.iterrows():
            rank = int(row.get("overall_rank", 0))
            combination_id = row["combination_id"]
            semantic = row["semantic_expander"]
            aggregator = row["aggregator"]
            avg_rank = row.get("avg_rank", 0)

            report.append(f"\n[Rank {rank}] {combination_id}")
            report.append(f"  Semantic Expander: {semantic}")
            report.append(f"  Aggregator: {aggregator}")
            report.append(f"  Average Rank: {avg_rank:.2f}")

            # 메트릭 점수
            metric_cols = [col for col in row.index
                           if col not in ["test_id", "combination_id", "semantic_expander",
                                          "aggregator", "n_samples", "avg_rank", "overall_rank"]
                           and not col.endswith("_rank")]
            for metric in metric_cols:
                score = row[metric]
                rank_col = f"{metric}_rank"
                metric_rank = int(row.get(rank_col, 0)) if rank_col in row.index else 0
                report.append(f"    - {metric}: {score:.4f} (rank: {metric_rank})")

        # 메트릭별 1위
        report.append("\n" + "-"*70)
        report.append("Metric-wise Best Combinations")
        report.append("-"*70)
        for metric, winner in metric_winners.items():
            combination_id = winner["combination_id"]
            score = winner[metric]
            report.append(f"\n[{metric}]")
            report.append(f"  Winner: {combination_id}")
            report.append(f"  Score: {score:.4f}")
            report.append(f"  Semantic: {winner['semantic_expander']}")
            report.append(f"  Aggregator: {winner['aggregator']}")

        report.append("\n" + "="*70)

        return "\n".join(report)

    def export_to_csv(self, output_path: Path):
        """
        결과를 CSV로 내보내기

        Args:
            output_path: CSV 파일 경로
        """
        df_ranked = self.calculate_rankings()
        df_ranked.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"[INFO] Results exported to: {output_path}")

    def export_report(self, output_path: Path):
        """
        리포트를 텍스트 파일로 내보내기

        Args:
            output_path: 텍스트 파일 경로
        """
        report = self.generate_report()
        output_path.write_text(report, encoding="utf-8")
        print(f"[INFO] Report exported to: {output_path}")


# =====================================================
# Visualization (Optional)
# =====================================================
def plot_results(df: pd.DataFrame, output_dir: Path):
    """
    결과 시각화 (matplotlib 필요)

    Args:
        df: 결과 DataFrame
        output_dir: 출력 디렉토리
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_style("whitegrid")

        # 메트릭 컬럼 추출
        metric_cols = [col for col in df.columns
                       if col not in ["test_id", "combination_id", "semantic_expander",
                                      "aggregator", "n_samples", "avg_rank", "overall_rank"]
                       and not col.endswith("_rank")]

        # 1. 메트릭별 점수 분포
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        for idx, metric in enumerate(metric_cols[:4]):
            ax = axes[idx]
            df_sorted = df.sort_values(metric, ascending=False)
            ax.barh(df_sorted["combination_id"], df_sorted[metric])
            ax.set_xlabel("Score")
            ax.set_title(f"{metric} Scores")
            ax.invert_yaxis()

        plt.tight_layout()
        plt.savefig(output_dir / "metric_scores.png", dpi=300)
        print(f"[INFO] Plot saved: {output_dir / 'metric_scores.png'}")

        # 2. Heatmap (조합 x 메트릭)
        if len(metric_cols) > 0:
            fig, ax = plt.subplots(figsize=(10, 12))
            heatmap_data = df.set_index("combination_id")[metric_cols]
            sns.heatmap(heatmap_data, annot=True, fmt=".3f", cmap="YlGnBu", ax=ax)
            ax.set_title("Metric Scores Heatmap")
            plt.tight_layout()
            plt.savefig(output_dir / "heatmap.png", dpi=300)
            print(f"[INFO] Plot saved: {output_dir / 'heatmap.png'}")

    except ImportError:
        print("[WARNING] matplotlib/seaborn not installed. Skipping visualization.")


# =====================================================
# Main
# =====================================================
def main():
    parser = argparse.ArgumentParser(
        description="Analyze RAGAS evaluation results"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to results JSON file"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export results to CSV"
    )
    parser.add_argument(
        "--export-report",
        action="store_true",
        help="Export report to text file"
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate visualization plots"
    )

    args = parser.parse_args()

    # 결과 파일 경로
    results_path = Path(args.input)
    if not results_path.is_absolute():
        results_path = FUSEKI_RESULTS_DIR / results_path

    # 분석기 생성
    analyzer = ResultsAnalyzer(results_path)

    # 리포트 생성 및 출력
    report = analyzer.generate_report()
    print(report)

    # CSV 내보내기
    if args.export_csv:
        csv_path = results_path.parent / f"{results_path.stem}_ranked.csv"
        analyzer.export_to_csv(csv_path)

    # 리포트 내보내기
    if args.export_report:
        report_path = results_path.parent / f"{results_path.stem}_report.txt"
        analyzer.export_report(report_path)

    # 시각화
    if args.plot:
        df_ranked = analyzer.calculate_rankings()
        plot_results(df_ranked, results_path.parent)


if __name__ == "__main__":
    main()
