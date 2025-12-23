"""
Example Usage of Fuseki RAGAS Evaluation System

이 파일은 RAGAS 평가 시스템의 사용 예시를 보여줍니다.
"""

import sys
from pathlib import Path

# ===== PROJECT ROOT 설정 =====
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ragas.fuseki import (
    ConfigManager,
    get_all_test_configs,
    RagasMetricsLoader
)


def example_1_config_manager():
    """예시 1: ConfigManager 사용"""
    print("="*70)
    print("Example 1: ConfigManager Usage")
    print("="*70)

    # ConfigManager 인스턴스 생성
    manager = ConfigManager()

    # 모든 조합 가져오기
    combinations = manager.get_all_combinations()
    print(f"\nTotal combinations: {len(combinations)}")

    # 처음 3개 조합 출력
    print("\nFirst 3 combinations:")
    for semantic, aggregator in combinations[:3]:
        combination_id = manager.get_combination_id(semantic, aggregator)
        print(f"  - {combination_id}")
        print(f"    Semantic: {semantic.value}")
        print(f"    Aggregator: {aggregator.value}")

    # 특정 조합에 대한 설정 생성
    semantic, aggregator = combinations[0]
    config = manager.create_node_config(semantic, aggregator)

    print(f"\nSample config for {config['combination_id']}:")
    print(f"  Thread Weights: {config['thread_weights']}")
    print()


def example_2_all_configs():
    """예시 2: 모든 테스트 설정 생성"""
    print("="*70)
    print("Example 2: Generate All Test Configs")
    print("="*70)

    # 모든 설정 가져오기
    configs = get_all_test_configs()

    print(f"\nGenerated {len(configs)} test configs")
    print("\nFirst 5 configs:")

    for config in configs[:5]:
        print(f"\n[Test {config['test_id']}/20] {config['combination_id']}")
        print(f"  Description: {config['description']}")
        print(f"  Semantic: {config['semantic_expander']['active_type']}")
        print(f"  Aggregator: {config['aggregator']['active_type']}")

    print()


def example_3_ragas_loader():
    """예시 3: RAGAS Metrics Loader 사용"""
    print("="*70)
    print("Example 3: RAGAS Metrics Loader Usage")
    print("="*70)

    # RAGAS Metrics Loader 생성
    loader = RagasMetricsLoader(debug=True)

    print("\nLoading RAGAS metrics...")
    try:
        loader.load_all()
        print(f"\nLoaded metrics: {list(loader.metrics.keys())}")

        # 샘플 데이터 생성
        sample = loader.create_sample(
            user_input="세조는 누구였나요?",
            response="세조는 조선의 제7대 왕입니다.",
            retrieved_contexts=[
                "세조는 조선의 제7대 왕이다.",
                "세조는 1455년에 즉위했다.",
                "세조는 수양대군이었다."
            ]
        )

        print(f"\nCreated sample:")
        print(f"  User Input: {sample.user_input}")
        print(f"  Response: {sample.response}")
        print(f"  Contexts: {len(sample.retrieved_contexts)}")

    except ImportError as e:
        print(f"\n[ERROR] Failed to load RAGAS: {e}")
        print("Please install RAGAS: pip install ragas")

    print()


def example_4_config_application():
    """예시 4: State에 설정 적용"""
    print("="*70)
    print("Example 4: Apply Config to State")
    print("="*70)

    manager = ConfigManager()
    configs = manager.generate_all_configs()

    # 첫 번째 설정 선택
    config = configs[0]

    # 가상의 GraphState 생성
    state = {
        "query": "세조는 누구였나요?",
        "thread_weights": {},
        "extracted_entities": []
    }

    print(f"\nApplying config: {config['combination_id']}")
    print(f"Original state: {state}")

    # 설정 적용
    updated_state = manager.apply_config_to_state(state, config)

    print(f"\nUpdated state:")
    print(f"  Thread Weights: {updated_state['thread_weights']}")
    print(f"  Test Config: {updated_state.get('test_config')}")
    print()


def main():
    """모든 예시 실행"""
    print("\n" + "="*70)
    print("Fuseki RAGAS Evaluation - Example Usage")
    print("="*70 + "\n")

    example_1_config_manager()
    example_2_all_configs()
    example_3_ragas_loader()
    example_4_config_application()

    print("="*70)
    print("All examples completed!")
    print("="*70)


if __name__ == "__main__":
    main()
