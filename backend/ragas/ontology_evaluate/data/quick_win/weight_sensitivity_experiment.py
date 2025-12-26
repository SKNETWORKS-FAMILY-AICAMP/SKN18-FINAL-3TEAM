#!/usr/bin/env python3
"""
Quick Win: Intent Preservation 가중치 민감도 실험
기존 실험 데이터로 다양한 가중치 설정에서 점수 재계산
"""

import json
from typing import Dict, List
from dataclasses import dataclass
import statistics

# 데이터 경로
DATA_PATH = "/home/claude/data_check/data/results/semantic_expander_ablation_summary.json"

@dataclass
class WeightConfig:
    name: str
    weights: Dict[str, float]
    
    def calculate_score(self, raw_metrics: Dict[str, float]) -> float:
        """가중치 적용하여 점수 계산"""
        total_weight = sum(self.weights.values())
        weighted_sum = sum(
            raw_metrics.get(metric, 0) * weight 
            for metric, weight in self.weights.items()
        )
        return weighted_sum / total_weight


# 실험할 가중치 설정들
WEIGHT_CONFIGS = [
    WeightConfig(
        name="baseline_equal",
        weights={
            "tbox_consistency": 1.0,
            "intent_preservation": 1.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 1.0,
            "convergence_utilization": 1.0,
            "property_group_selection": 1.0,
        }
    ),
    WeightConfig(
        name="intent_x2",
        weights={
            "tbox_consistency": 1.0,
            "intent_preservation": 2.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 1.0,
            "convergence_utilization": 1.0,
            "property_group_selection": 1.0,
        }
    ),
    WeightConfig(
        name="intent_x3",
        weights={
            "tbox_consistency": 1.0,
            "intent_preservation": 3.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 1.0,
            "convergence_utilization": 1.0,
            "property_group_selection": 1.0,
        }
    ),
    WeightConfig(
        name="intent_x2_tbox_x1.5",
        weights={
            "tbox_consistency": 1.5,
            "intent_preservation": 2.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 1.0,
            "convergence_utilization": 1.0,
            "property_group_selection": 1.0,
        }
    ),
    WeightConfig(
        name="intent_x3_tbox_x2",
        weights={
            "tbox_consistency": 2.0,
            "intent_preservation": 3.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 1.0,
            "convergence_utilization": 1.0,
            "property_group_selection": 1.0,
        }
    ),
    WeightConfig(
        name="intent_x3_evidence_x0.5",
        weights={
            "tbox_consistency": 1.0,
            "intent_preservation": 3.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 0.5,
            "convergence_utilization": 1.0,
            "property_group_selection": 0.5,
        }
    ),
    WeightConfig(
        name="core_metrics_only",
        weights={
            "tbox_consistency": 2.0,
            "intent_preservation": 3.0,
            "relation_coherence": 1.5,
            "triple_validity": 1.5,
            "evidence_diversity": 0.5,
            "convergence_utilization": 0.5,
            "property_group_selection": 0.5,
        }
    ),
    WeightConfig(
        name="aggressive_intent",
        weights={
            "tbox_consistency": 1.0,
            "intent_preservation": 5.0,
            "relation_coherence": 1.0,
            "triple_validity": 1.0,
            "evidence_diversity": 0.5,
            "convergence_utilization": 0.5,
            "property_group_selection": 0.5,
        }
    ),
]


def load_data() -> List[Dict]:
    """실험 데이터 로드"""
    with open(DATA_PATH, 'r') as f:
        return json.load(f)


def analyze_weight_config(data: List[Dict], config: WeightConfig) -> Dict:
    """특정 가중치 설정으로 전체 데이터 분석"""
    
    # 실험별 그룹화
    experiments = {}
    for item in data:
        exp_name = item['experiment_name'].replace('semantic_expander_', '')
        if exp_name not in experiments:
            experiments[exp_name] = []
        
        # 새 가중치로 점수 재계산
        new_score = config.calculate_score(item['raw_metrics'])
        experiments[exp_name].append({
            'query': item['query'],
            'query_type': item['query_type'],
            'original_score': item['intent_aware_score'],
            'new_score': new_score,
            'raw_metrics': item['raw_metrics']
        })
    
    # 실험별 평균 계산
    results = {}
    for exp_name, items in experiments.items():
        original_scores = [i['original_score'] for i in items]
        new_scores = [i['new_score'] for i in items]
        results[exp_name] = {
            'original_mean': statistics.mean(original_scores),
            'new_mean': statistics.mean(new_scores),
            'original_std': statistics.stdev(original_scores),
            'new_std': statistics.stdev(new_scores),
            'items': items
        }
    
    return results


def compare_baseline_vs_full(results: Dict) -> Dict:
    """Baseline vs Full 비교"""
    baseline = results.get('baseline', {})
    full = results.get('full', {})
    
    return {
        'baseline_mean': baseline.get('new_mean', 0),
        'full_mean': full.get('new_mean', 0),
        'gap': baseline.get('new_mean', 0) - full.get('new_mean', 0),
        'baseline_wins': baseline.get('new_mean', 0) > full.get('new_mean', 0)
    }


def analyze_query_type_performance(results: Dict) -> Dict:
    """쿼리 타입별 성능 분석"""
    query_types = ['factual', 'causal', 'comparative', 'deep_analysis']
    analysis = {}
    
    for qt in query_types:
        qt_results = {}
        for exp_name, exp_data in results.items():
            qt_items = [i for i in exp_data['items'] if i['query_type'] == qt]
            if qt_items:
                qt_results[exp_name] = statistics.mean([i['new_score'] for i in qt_items])
        
        # 최고 성능 설정 찾기
        if qt_results:
            best_exp = max(qt_results, key=qt_results.get)
            analysis[qt] = {
                'scores': qt_results,
                'best': best_exp,
                'best_score': qt_results[best_exp]
            }
    
    return analysis


def find_ranking_changes(data: List[Dict], config: WeightConfig) -> List[Dict]:
    """원래 점수와 새 점수 간 순위 변화가 큰 케이스 찾기"""
    changes = []
    
    # 쿼리별로 그룹화
    queries = {}
    for item in data:
        query = item['query']
        if query not in queries:
            queries[query] = []
        
        new_score = config.calculate_score(item['raw_metrics'])
        queries[query].append({
            'exp': item['experiment_name'].replace('semantic_expander_', ''),
            'original': item['intent_aware_score'],
            'new': new_score
        })
    
    # 순위 변화 계산
    for query, exps in queries.items():
        original_ranking = sorted(exps, key=lambda x: x['original'], reverse=True)
        new_ranking = sorted(exps, key=lambda x: x['new'], reverse=True)
        
        original_best = original_ranking[0]['exp']
        new_best = new_ranking[0]['exp']
        
        if original_best != new_best:
            changes.append({
                'query': query,
                'original_best': original_best,
                'new_best': new_best,
                'original_ranking': [e['exp'] for e in original_ranking],
                'new_ranking': [e['exp'] for e in new_ranking]
            })
    
    return changes


def main():
    print("=" * 80)
    print("Quick Win: Intent Preservation 가중치 민감도 실험")
    print("=" * 80)
    
    # 데이터 로드
    data = load_data()
    print(f"\n총 {len(data)}개 케이스 로드 완료")
    
    # 각 가중치 설정별 분석
    all_results = {}
    
    print("\n" + "=" * 80)
    print("1. 가중치 설정별 전체 성능 비교")
    print("=" * 80)
    
    print(f"\n{'설정':<25} {'Baseline':>10} {'Full':>10} {'Gap':>10} {'Winner':>10}")
    print("-" * 70)
    
    for config in WEIGHT_CONFIGS:
        results = analyze_weight_config(data, config)
        all_results[config.name] = results
        
        comparison = compare_baseline_vs_full(results)
        winner = "Baseline" if comparison['baseline_wins'] else "Full"
        
        print(f"{config.name:<25} {comparison['baseline_mean']:>10.4f} {comparison['full_mean']:>10.4f} {comparison['gap']:>+10.4f} {winner:>10}")
    
    # 상세 분석: 가장 유망한 설정
    print("\n" + "=" * 80)
    print("2. 실험 설정별 상세 점수 (intent_x3 기준)")
    print("=" * 80)
    
    best_config = WEIGHT_CONFIGS[2]  # intent_x3
    results = all_results[best_config.name]
    
    print(f"\n{'실험 설정':<25} {'평균 점수':>12} {'표준편차':>12}")
    print("-" * 50)
    for exp_name in ['baseline', 'temporal_only', 'causal_chain_only', 'pgvector_only', 'full']:
        if exp_name in results:
            print(f"{exp_name:<25} {results[exp_name]['new_mean']:>12.4f} {results[exp_name]['new_std']:>12.4f}")
    
    # 쿼리 타입별 분석
    print("\n" + "=" * 80)
    print("3. 쿼리 타입별 최적 설정 (intent_x3 기준)")
    print("=" * 80)
    
    qt_analysis = analyze_query_type_performance(results)
    
    print(f"\n{'쿼리 타입':<15} {'최적 설정':<20} {'점수':>10}")
    print("-" * 50)
    for qt, analysis in qt_analysis.items():
        print(f"{qt:<15} {analysis['best']:<20} {analysis['best_score']:>10.4f}")
    
    # 순위 변화 분석
    print("\n" + "=" * 80)
    print("4. 가중치 변경 시 순위 변화 케이스")
    print("=" * 80)
    
    for config in [WEIGHT_CONFIGS[2], WEIGHT_CONFIGS[6]]:  # intent_x3, core_metrics_only
        changes = find_ranking_changes(data, config)
        print(f"\n[{config.name}] 순위 변화: {len(changes)}/20 쿼리")
        
        if changes:
            print(f"  변화 예시:")
            for change in changes[:3]:
                print(f"    - {change['query'][:30]}...")
                print(f"      {change['original_best']} → {change['new_best']}")
    
    # 최종 권장사항
    print("\n" + "=" * 80)
    print("5. 권장 가중치 설정")
    print("=" * 80)
    
    # Gap이 가장 큰 설정 찾기
    best_gap = 0
    best_config_name = ""
    for config in WEIGHT_CONFIGS:
        results = all_results[config.name]
        comparison = compare_baseline_vs_full(results)
        if comparison['gap'] > best_gap:
            best_gap = comparison['gap']
            best_config_name = config.name
    
    print(f"\n✅ Baseline-Full Gap 최대화 설정: {best_config_name} (gap: {best_gap:.4f})")
    
    # 해당 설정의 가중치 출력
    for config in WEIGHT_CONFIGS:
        if config.name == best_config_name:
            print(f"\n권장 가중치:")
            for metric, weight in config.weights.items():
                print(f"  {metric}: {weight}")
    
    # 결과 저장
    output = {
        'weight_configs': [{
            'name': c.name,
            'weights': c.weights,
            'baseline_mean': all_results[c.name]['baseline']['new_mean'],
            'full_mean': all_results[c.name]['full']['new_mean'],
            'gap': all_results[c.name]['baseline']['new_mean'] - all_results[c.name]['full']['new_mean']
        } for c in WEIGHT_CONFIGS],
        'best_config': best_config_name,
        'best_gap': best_gap
    }
    
    with open('/home/claude/weight_experiment_results.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: /home/claude/weight_experiment_results.json")


if __name__ == "__main__":
    main()
