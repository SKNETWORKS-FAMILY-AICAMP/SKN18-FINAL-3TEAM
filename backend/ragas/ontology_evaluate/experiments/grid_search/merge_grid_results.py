"""
Grid Search 결과 통합 스크립트

4개 배치의 결과를 통합하고 최적 설정을 분석합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_grid_results --timestamp 20241226_153000
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "backend" / "ragas" / "ontology_evaluate" / "data"
RESULTS_DIR = DATA_DIR / "grid_search_results"


def merge_batch_results(timestamp: str) -> dict:
    """4개 배치 결과 통합"""
    all_results = []
    batch_summaries = []
    
    for batch_num in range(1, 5):
        batch_file = RESULTS_DIR / f"batch_{batch_num}_results_{timestamp}.json"
        
        if not batch_file.exists():
            print(f"⚠️  Batch {batch_num} 결과 파일 없음: {batch_file}")
            continue
        
        with open(batch_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
        
        batch_results = batch_data.get("results", [])
        all_results.extend(batch_results)
        
        batch_summary = {
            "batch_num": batch_num,
            "total_configs": batch_data.get("total_configs", 0),
            "total_time": batch_data.get("total_time", 0)
        }
        batch_summaries.append(batch_summary)
        
        print(f"✓ Batch {batch_num} 로드: {len(batch_results)}개 설정")
    
    return all_results, batch_summaries


def analyze_results(results: list) -> dict:
    """
    결과 분석 및 최적 설정 찾기
    """
    # 전체 설정 정렬
    sorted_by_score = sorted(results, key=lambda x: x["mean_score"], reverse=True)
    
    # 파라미터별 분석
    se_analysis = defaultdict(list)
    thread_analysis = defaultdict(list)
    boost_analysis = defaultdict(list)
    
    for r in results:
        config = r["config"]
        score = r["mean_score"]
        
        # Semantic Expander 분석
        se_key = f"temporal={config['semantic_expander']['temporal']}, " \
                 f"causal={config['semantic_expander']['causal_chain']}"
        se_analysis[se_key].append(score)
        
        # Thread 분석
        thread_key = f"in={config['thread_weights']['incoming_relations']}, " \
                     f"out={config['thread_weights']['outgoing_relations']}"
        thread_analysis[thread_key].append(score)
        
        # Boost 분석
        boost_key = f"norm={config['entity_boost']['normalized']}, " \
                    f"partial={config['entity_boost']['partial']}"
        boost_analysis[boost_key].append(score)
    
    # 각 파라미터별 평균 계산
    se_means = {k: sum(v)/len(v) for k, v in se_analysis.items()}
    thread_means = {k: sum(v)/len(v) for k, v in thread_analysis.items()}
    boost_means = {k: sum(v)/len(v) for k, v in boost_analysis.items()}
    
    # 최적 파라미터 찾기
    best_se = max(se_means.items(), key=lambda x: x[1])
    best_thread = max(thread_means.items(), key=lambda x: x[1])
    best_boost = max(boost_means.items(), key=lambda x: x[1])
    
    return {
        "top_configs": sorted_by_score[:10],
        "worst_configs": sorted_by_score[-5:],
        "parameter_analysis": {
            "semantic_expander": dict(sorted(se_means.items(), key=lambda x: x[1], reverse=True)),
            "thread_weights": dict(sorted(thread_means.items(), key=lambda x: x[1], reverse=True)),
            "entity_boost": dict(sorted(boost_means.items(), key=lambda x: x[1], reverse=True))
        },
        "best_parameters": {
            "semantic_expander": best_se,
            "thread_weights": best_thread,
            "entity_boost": best_boost
        },
        "overall_stats": {
            "total_configs": len(results),
            "mean_score": sum(r["mean_score"] for r in results) / len(results),
            "max_score": max(r["mean_score"] for r in results),
            "min_score": min(r["mean_score"] for r in results)
        }
    }


def generate_report(analysis: dict, timestamp: str) -> str:
    """분석 결과를 마크다운 리포트로 생성"""
    lines = []
    
    lines.append("# Grid Search 결과 리포트\n")
    lines.append(f"**실행 시간**: {timestamp}\n")
    
    # 전체 통계
    stats = analysis["overall_stats"]
    lines.append("\n## 전체 통계\n")
    lines.append(f"| 항목 | 값 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 총 설정 수 | {stats['total_configs']}개 |")
    lines.append(f"| 평균 점수 | {stats['mean_score']:.4f} |")
    lines.append(f"| 최고 점수 | {stats['max_score']:.4f} |")
    lines.append(f"| 최저 점수 | {stats['min_score']:.4f} |")
    
    # 최적 파라미터
    best = analysis["best_parameters"]
    lines.append("\n## 🏆 최적 파라미터\n")
    lines.append(f"| 파라미터 | 최적값 | 평균 점수 |")
    lines.append(f"|----------|--------|----------|")
    lines.append(f"| Semantic Expander | {best['semantic_expander'][0]} | {best['semantic_expander'][1]:.4f} |")
    lines.append(f"| Thread Weights | {best['thread_weights'][0]} | {best['thread_weights'][1]:.4f} |")
    lines.append(f"| Entity Boost | {best['entity_boost'][0]} | {best['entity_boost'][1]:.4f} |")
    
    # 상위 10개 설정
    lines.append("\n## 상위 10개 설정\n")
    lines.append(f"| 순위 | 설정 이름 | 평균 점수 | 성공률 |")
    lines.append(f"|------|----------|----------|--------|")
    for i, config in enumerate(analysis["top_configs"], 1):
        success_rate = config["success_count"] / config["total_queries"] * 100
        lines.append(f"| {i} | {config['config_name']} | {config['mean_score']:.4f} | {success_rate:.0f}% |")
    
    # 파라미터별 상세 분석
    lines.append("\n## 파라미터별 상세 분석\n")
    
    lines.append("\n### Semantic Expander\n")
    lines.append(f"| 설정 | 평균 점수 |")
    lines.append(f"|------|----------|")
    for k, v in analysis["parameter_analysis"]["semantic_expander"].items():
        lines.append(f"| {k} | {v:.4f} |")
    
    lines.append("\n### Thread Weights\n")
    lines.append(f"| 설정 | 평균 점수 |")
    lines.append(f"|------|----------|")
    for k, v in analysis["parameter_analysis"]["thread_weights"].items():
        lines.append(f"| {k} | {v:.4f} |")
    
    lines.append("\n### Entity Boost\n")
    lines.append(f"| 설정 | 평균 점수 |")
    lines.append(f"|------|----------|")
    for k, v in analysis["parameter_analysis"]["entity_boost"].items():
        lines.append(f"| {k} | {v:.4f} |")
    
    # 권장 설정
    lines.append("\n## 📋 권장 설정 (config.py 반영용)\n")
    lines.append("```python")
    lines.append("# Grid Search 결과 기반 최적 설정")
    lines.append(f"# {timestamp}")
    lines.append("")
    
    # 최상위 설정에서 값 추출
    top_config = analysis["top_configs"][0]["config"]
    lines.append(f"# Semantic Expander")
    lines.append(f"FIXED_SCORE_TEMPORAL = {1.0 if top_config['semantic_expander']['temporal'] else 0.0}")
    lines.append(f"FIXED_SCORE_CAUSAL_CHAIN = {1.0 if top_config['semantic_expander']['causal_chain'] else 0.0}")
    lines.append(f"FIXED_SCORE_PGVECTOR = 0.0")
    lines.append("")
    lines.append(f"# Thread Weights")
    lines.append(f"THREAD_WEIGHT_INCOMING_RELATIONS = {top_config['thread_weights']['incoming_relations']}")
    lines.append(f"THREAD_WEIGHT_OUTGOING_RELATIONS = {top_config['thread_weights']['outgoing_relations']}")
    lines.append("")
    lines.append(f"# Entity Boost")
    lines.append(f"QUERY_ENTITY_MATCH_BOOST_NORMALIZED = {top_config['entity_boost']['normalized']}")
    lines.append(f"QUERY_ENTITY_MATCH_BOOST_PARTIAL = {top_config['entity_boost']['partial']}")
    lines.append("```")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Grid Search 결과 통합")
    parser.add_argument("--timestamp", type=str, required=True, help="실행 타임스탬프")
    args = parser.parse_args()
    
    timestamp = args.timestamp
    
    print("=" * 80)
    print("Grid Search 결과 통합")
    print("=" * 80)
    print(f"타임스탬프: {timestamp}")
    
    # 1. 배치 결과 통합
    all_results, batch_summaries = merge_batch_results(timestamp)
    print(f"\n총 {len(all_results)}개 설정 결과 로드")
    
    if not all_results:
        print("❌ 결과가 없습니다.")
        return
    
    # 2. 결과 분석
    print("\n분석 중...")
    analysis = analyze_results(all_results)
    
    # 3. 통합 결과 저장
    merged_file = RESULTS_DIR / f"grid_search_merged_{timestamp}.json"
    merged_data = {
        "timestamp": timestamp,
        "batch_summaries": batch_summaries,
        "analysis": {
            "overall_stats": analysis["overall_stats"],
            "best_parameters": {
                k: {"value": v[0], "score": v[1]} 
                for k, v in analysis["best_parameters"].items()
            },
            "parameter_analysis": analysis["parameter_analysis"]
        },
        "top_configs": [
            {
                "rank": i+1,
                "config_name": c["config_name"],
                "mean_score": c["mean_score"],
                "config": c["config"]
            }
            for i, c in enumerate(analysis["top_configs"])
        ],
        "all_results": all_results
    }
    
    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 통합 결과 저장: {merged_file}")
    
    # 4. 리포트 생성
    report = generate_report(analysis, timestamp)
    report_file = RESULTS_DIR / f"grid_search_report_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✓ 리포트 저장: {report_file}")
    
    # 5. 결과 출력
    print("\n" + "=" * 80)
    print("Grid Search 결과 요약")
    print("=" * 80)
    
    print(f"\n📊 전체 통계")
    print(f"  평균 점수: {analysis['overall_stats']['mean_score']:.4f}")
    print(f"  최고 점수: {analysis['overall_stats']['max_score']:.4f}")
    print(f"  최저 점수: {analysis['overall_stats']['min_score']:.4f}")
    
    print(f"\n🏆 최적 파라미터")
    for param, (value, score) in analysis["best_parameters"].items():
        print(f"  {param}: {value} (점수: {score:.4f})")
    
    print(f"\n🥇 상위 5개 설정")
    for i, config in enumerate(analysis["top_configs"][:5], 1):
        print(f"  {i}. {config['config_name']}: {config['mean_score']:.4f}")
    
    print("\n" + "=" * 80)
    print("통합 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()