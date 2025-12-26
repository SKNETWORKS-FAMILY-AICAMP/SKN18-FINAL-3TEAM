#!/usr/bin/env python3
"""
Quick Win: Thread Ablation & Entity Boost 가중치 민감도 실험
기존 실험 데이터로 다양한 가중치 설정에서 점수 재계산
"""

import json
from typing import Dict, List
from dataclasses import dataclass
import statistics

# 데이터 경로
THREAD_PATH = "/home/claude/data_check/data/results/thread_ablation_summary.json"
ENTITY_BOOST_PATH = "/home/claude/data_check/data/results/entity_boost_ablation_summary.json"

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
    WeightConfig(
        name="triple_focused",
        weights={
            "tbox_consistency": 2.0,
            "intent_preservation": 3.0,
            "relation_coherence": 2.0,
            "triple_validity": 2.0,
            "evidence_diversity": 0.5,
            "convergence_utilization": 0.5,
            "property_group_selection": 0.5,
        }
    ),
]


def load_data(path: str) -> List[Dict]:
    """실험 데이터 로드"""
    with open(path, 'r') as f:
        return json.load(f)


def analyze_experiment(data: List[Dict], config: WeightConfig, exp_prefix: str) -> Dict:
    """특정 가중치 설정으로 전체 데이터 분석"""
    
    experiments = {}
    for item in data:
        exp_name = item['experiment_name'].replace(exp_prefix, '')
        if exp_name not in experiments:
            experiments[exp_name] = []
        
        new_score = config.calculate_score(item['raw_metrics'])
        experiments[exp_name].append({
            'query': item['query'],
            'query_type': item['query_type'],
            'original_score': item['intent_aware_score'],
            'new_score': new_score,
            'raw_metrics': item['raw_metrics']
        })
    
    results = {}
    for exp_name, items in experiments.items():
        original_scores = [i['original_score'] for i in items]
        new_scores = [i['new_score'] for i in items]
        results[exp_name] = {
            'original_mean': statistics.mean(original_scores),
            'new_mean': statistics.mean(new_scores),
            'n': len(items),
            'items': items
        }
    
    return results


def find_best_worst(results: Dict) -> Dict:
    """최고/최저 성능 설정 찾기"""
    sorted_by_new = sorted(results.items(), key=lambda x: x[1]['new_mean'], reverse=True)
    return {
        'best': sorted_by_new[0],
        'worst': sorted_by_new[-1],
        'gap': sorted_by_new[0][1]['new_mean'] - sorted_by_new[-1][1]['new_mean']
    }


def run_thread_ablation_experiment():
    """Thread Ablation 실험"""
    print("\n" + "=" * 80)
    print("THREAD ABLATION 가중치 민감도 실험")
    print("=" * 80)
    
    data = load_data(THREAD_PATH)
    print(f"총 {len(data)}개 케이스 로드")
    
    all_results = {}
    
    print(f"\n{'설정':<25} {'Best':>25} {'Worst':>25} {'Gap':>10}")
    print("-" * 90)
    
    for config in WEIGHT_CONFIGS:
        results = analyze_experiment(data, config, 'thread_')
        all_results[config.name] = results
        
        bw = find_best_worst(results)
        best_name = bw['best'][0]
        worst_name = bw['worst'][0]
        best_score = bw['best'][1]['new_mean']
        worst_score = bw['worst'][1]['new_mean']
        
        print(f"{config.name:<25} {best_name:>15}({best_score:.4f}) {worst_name:>15}({worst_score:.4f}) {bw['gap']:>10.4f}")
    
    # 상세 분석: aggressive_intent
    print("\n" + "-" * 80)
    print("상세 분석: aggressive_intent 설정")
    print("-" * 80)
    
    results = all_results['aggressive_intent']
    print(f"\n{'설정':<35} {'Original':>12} {'New Score':>12} {'변화':>12}")
    print("-" * 75)
    
    for exp_name in ['baseline', 'without_outgoing_relations', 'without_incoming_relations',
                     'without_entity_properties', 'without_connected_entities', 'without_type_and_summary']:
        if exp_name in results:
            orig = results[exp_name]['original_mean']
            new = results[exp_name]['new_mean']
            print(f"{exp_name:<35} {orig:>12.4f} {new:>12.4f} {new-orig:>+12.4f}")
    
    return all_results


def run_entity_boost_experiment():
    """Entity Boost Ablation 실험"""
    print("\n" + "=" * 80)
    print("ENTITY BOOST ABLATION 가중치 민감도 실험")
    print("=" * 80)
    
    data = load_data(ENTITY_BOOST_PATH)
    print(f"총 {len(data)}개 케이스 로드")
    
    all_results = {}
    
    print(f"\n{'설정':<25} {'Best':>25} {'Worst':>25} {'Gap':>10}")
    print("-" * 90)
    
    for config in WEIGHT_CONFIGS:
        results = analyze_experiment(data, config, 'entity_boost_')
        all_results[config.name] = results
        
        bw = find_best_worst(results)
        best_name = bw['best'][0]
        worst_name = bw['worst'][0]
        best_score = bw['best'][1]['new_mean']
        worst_score = bw['worst'][1]['new_mean']
        
        print(f"{config.name:<25} {best_name:>15}({best_score:.4f}) {worst_name:>15}({worst_score:.4f}) {bw['gap']:>10.4f}")
    
    # 상세 분석: aggressive_intent
    print("\n" + "-" * 80)
    print("상세 분석: aggressive_intent 설정")
    print("-" * 80)
    
    results = all_results['aggressive_intent']
    print(f"\n{'설정':<25} {'Original':>12} {'New Score':>12} {'변화':>12}")
    print("-" * 55)
    
    for exp_name in ['exact_match', 'normalized_match', 'partial_match', 'penalty_match']:
        if exp_name in results:
            orig = results[exp_name]['original_mean']
            new = results[exp_name]['new_mean']
            print(f"{exp_name:<25} {orig:>12.4f} {new:>12.4f} {new-orig:>+12.4f}")
    
    return all_results


def compare_all_experiments():
    """모든 실험 결과 종합 비교"""
    print("\n" + "=" * 80)
    print("전체 실험 종합 비교")
    print("=" * 80)
    
    # 데이터 로드
    se_data = load_data("/home/claude/data_check/data/results/semantic_expander_ablation_summary.json")
    thread_data = load_data(THREAD_PATH)
    eb_data = load_data(ENTITY_BOOST_PATH)
    
    config = WEIGHT_CONFIGS[6]  # aggressive_intent
    
    print(f"\n가중치 설정: {config.name}")
    print(f"weights: intent={config.weights['intent_preservation']}, tbox={config.weights['tbox_consistency']}")
    
    # Semantic Expander
    se_results = analyze_experiment(se_data, config, 'semantic_expander_')
    se_bw = find_best_worst(se_results)
    
    # Thread
    thread_results = analyze_experiment(thread_data, config, 'thread_')
    thread_bw = find_best_worst(thread_results)
    
    # Entity Boost
    eb_results = analyze_experiment(eb_data, config, 'entity_boost_')
    eb_bw = find_best_worst(eb_results)
    
    print(f"\n{'실험':<25} {'Best':>30} {'Worst':>30} {'Gap':>10}")
    print("-" * 100)
    
    print(f"{'Semantic Expander':<25} {se_bw['best'][0]:>20}({se_bw['best'][1]['new_mean']:.4f}) {se_bw['worst'][0]:>20}({se_bw['worst'][1]['new_mean']:.4f}) {se_bw['gap']:>10.4f}")
    print(f"{'Thread Ablation':<25} {thread_bw['best'][0]:>20}({thread_bw['best'][1]['new_mean']:.4f}) {thread_bw['worst'][0]:>20}({thread_bw['worst'][1]['new_mean']:.4f}) {thread_bw['gap']:>10.4f}")
    print(f"{'Entity Boost':<25} {eb_bw['best'][0]:>20}({eb_bw['best'][1]['new_mean']:.4f}) {eb_bw['worst'][0]:>20}({eb_bw['worst'][1]['new_mean']:.4f}) {eb_bw['gap']:>10.4f}")
    
    # 결과 저장
    output = {
        'weight_config': config.name,
        'weights': config.weights,
        'semantic_expander': {
            'best': se_bw['best'][0],
            'best_score': se_bw['best'][1]['new_mean'],
            'worst': se_bw['worst'][0],
            'worst_score': se_bw['worst'][1]['new_mean'],
            'gap': se_bw['gap'],
            'all_scores': {k: v['new_mean'] for k, v in se_results.items()}
        },
        'thread_ablation': {
            'best': thread_bw['best'][0],
            'best_score': thread_bw['best'][1]['new_mean'],
            'worst': thread_bw['worst'][0],
            'worst_score': thread_bw['worst'][1]['new_mean'],
            'gap': thread_bw['gap'],
            'all_scores': {k: v['new_mean'] for k, v in thread_results.items()}
        },
        'entity_boost': {
            'best': eb_bw['best'][0],
            'best_score': eb_bw['best'][1]['new_mean'],
            'worst': eb_bw['worst'][0],
            'worst_score': eb_bw['worst'][1]['new_mean'],
            'gap': eb_bw['gap'],
            'all_scores': {k: v['new_mean'] for k, v in eb_results.items()}
        }
    }
    
    with open('/home/claude/all_experiments_weight_results.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: /home/claude/all_experiments_weight_results.json")
    
    return output


def analyze_ranking_changes():
    """가중치 변경에 따른 순위 변화 분석"""
    print("\n" + "=" * 80)
    print("가중치 변경에 따른 최적 설정 변화")
    print("=" * 80)
    
    thread_data = load_data(THREAD_PATH)
    eb_data = load_data(ENTITY_BOOST_PATH)
    
    print("\n### Thread Ablation ###")
    print(f"{'가중치 설정':<25} {'1위':<30} {'2위':<30}")
    print("-" * 90)
    
    for config in WEIGHT_CONFIGS:
        results = analyze_experiment(thread_data, config, 'thread_')
        sorted_results = sorted(results.items(), key=lambda x: x[1]['new_mean'], reverse=True)
        first = f"{sorted_results[0][0]}({sorted_results[0][1]['new_mean']:.4f})"
        second = f"{sorted_results[1][0]}({sorted_results[1][1]['new_mean']:.4f})"
        print(f"{config.name:<25} {first:<30} {second:<30}")
    
    print("\n### Entity Boost Ablation ###")
    print(f"{'가중치 설정':<25} {'1위':<30} {'2위':<30}")
    print("-" * 90)
    
    for config in WEIGHT_CONFIGS:
        results = analyze_experiment(eb_data, config, 'entity_boost_')
        sorted_results = sorted(results.items(), key=lambda x: x[1]['new_mean'], reverse=True)
        first = f"{sorted_results[0][0]}({sorted_results[0][1]['new_mean']:.4f})"
        second = f"{sorted_results[1][0]}({sorted_results[1][1]['new_mean']:.4f})"
        print(f"{config.name:<25} {first:<30} {second:<30}")


def main():
    print("=" * 80)
    print("Quick Win: Thread & Entity Boost 가중치 민감도 실험")
    print("=" * 80)
    
    # Thread Ablation 실험
    thread_results = run_thread_ablation_experiment()
    
    # Entity Boost 실험
    eb_results = run_entity_boost_experiment()
    
    # 순위 변화 분석
    analyze_ranking_changes()
    
    # 전체 종합
    all_results = compare_all_experiments()
    
    # 최종 권장사항
    print("\n" + "=" * 80)
    print("최종 권장사항")
    print("=" * 80)
    
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ 권장 가중치 (aggressive_intent)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ intent_preservation: 5.0  ← 핵심 메트릭                                      │
│ tbox_consistency: 1.0                                                        │
│ relation_coherence: 1.0                                                      │
│ triple_validity: 1.0                                                         │
│ evidence_diversity: 0.5   ← 하향                                             │
│ convergence_utilization: 0.5  ← 하향                                         │
│ property_group_selection: 0.5  ← 하향                                        │
└─────────────────────────────────────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    main()
