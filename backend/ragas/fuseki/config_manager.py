"""
Configuration Manager for Node Activation/Deactivation

이 모듈은 semantic_expander와 aggregator의 조합을 관리합니다.
총 20가지 조합 (4 semantic_expanders × 5 aggregators)을 테스트합니다.
"""

from typing import Dict, List, Tuple
from enum import Enum


class SemanticExpanderType(Enum):
    """
    Semantic Expander 타입 (4가지)

    엔티티 추출 후 의미론적으로 관련된 엔티티를 확장하는 방법:
    - TEMPORAL: 시간적 맥락 확장 (±10년 이내 이벤트)
    - CATEGORY: 카테고리 기반 주제 확장 (동일 카테고리 이벤트)
    - CAUSAL_CHAIN: 인과관계 체인 확장 (leadsTo, causedBy)
    - PGVECTOR: 벡터 유사도 확장 (pgvector)
    """
    TEMPORAL = "temporal"
    CATEGORY = "category"
    CAUSAL_CHAIN = "causal_chain"
    PGVECTOR = "pgvector"


class AggregatorType(Enum):
    """
    Aggregator 타입 (5가지)

    Parallel Knowledge Retrieval의 Thread 타입:
    - OUTGOING_RELATIONS: 나가는 관계 (엔티티 → ?)
    - INCOMING_RELATIONS: 들어오는 관계 (? → 엔티티)
    - ENTITY_PROPERTIES: 엔티티 속성 (리터럴 값)
    - CONNECTED_ENTITIES: 연결된 엔티티 (2-hop)
    - TYPE_AND_SUMMARY: 타입과 요약 정보
    """
    OUTGOING_RELATIONS = "outgoing_relations"
    INCOMING_RELATIONS = "incoming_relations"
    ENTITY_PROPERTIES = "entity_properties"
    CONNECTED_ENTITIES = "connected_entities"
    TYPE_AND_SUMMARY = "type_and_summary"


class ConfigManager:
    """
    노드 조합 설정 관리자

    20가지 조합:
    - Semantic Expander: 4가지 (outgoing, incoming, properties, connected)
    - Aggregator: 5가지 (type_summary, outgoing, incoming, properties, connected)
    """

    def __init__(self):
        self.semantic_expanders = list(SemanticExpanderType)
        self.aggregators = list(AggregatorType)

    def get_all_combinations(self) -> List[Tuple[SemanticExpanderType, AggregatorType]]:
        """
        모든 조합 생성 (총 20가지)

        Returns:
            [(semantic_expander, aggregator), ...]
        """
        combinations = []
        for semantic in self.semantic_expanders:
            for aggregator in self.aggregators:
                combinations.append((semantic, aggregator))
        return combinations

    def get_combination_id(
        self,
        semantic: SemanticExpanderType,
        aggregator: AggregatorType
    ) -> str:
        """
        조합의 고유 ID 생성

        예: "outgoing_relations__type_and_summary"
        """
        return f"{semantic.value}__{aggregator.value}"

    def create_node_config(
        self,
        semantic: SemanticExpanderType,
        aggregator: AggregatorType,
        base_weights: Dict[str, float] = None
    ) -> Dict:
        """
        특정 조합에 대한 노드 설정 생성

        Args:
            semantic: 활성화할 semantic expander 방법
            aggregator: 활성화할 aggregator (thread 타입)
            base_weights: 기본 가중치 (모두 1.0으로 설정)

        Returns:
            노드 설정 딕셔너리
        """
        if base_weights is None:
            # 모든 Thread 가중치를 1.0으로 설정
            base_weights = {
                "outgoing_relations": 1.0,
                "incoming_relations": 1.0,
                "entity_properties": 1.0,
                "connected_entities": 1.0,
                "type_and_summary": 1.0
            }

        # Semantic Expander 가중치
        semantic_weights = {
            "temporal": 0.0,
            "category": 0.0,
            "causal_chain": 0.0,
            "pgvector": 0.0
        }
        semantic_weights[semantic.value] = 1.0  # 선택된 방법만 활성화

        # Aggregator (Thread) 가중치
        thread_weights = {
            "outgoing_relations": 0.0,
            "incoming_relations": 0.0,
            "entity_properties": 0.0,
            "connected_entities": 0.0,
            "type_and_summary": 0.0
        }
        thread_weights[aggregator.value] = 1.0  # 선택된 Thread만 활성화

        config = {
            "combination_id": self.get_combination_id(semantic, aggregator),
            "semantic_expander": {
                "active_type": semantic.value,
                "weights": semantic_weights
            },
            "aggregator": {
                "active_type": aggregator.value,
                "weights": thread_weights
            },
            "thread_weights": thread_weights  # parallel_knowledge_retrieval_node에서 사용
        }

        return config

    def generate_all_configs(self) -> List[Dict]:
        """
        모든 20가지 조합의 설정 생성

        Returns:
            20개의 노드 설정 리스트
        """
        configs = []
        combinations = self.get_all_combinations()

        for idx, (semantic, aggregator) in enumerate(combinations, 1):
            config = self.create_node_config(semantic, aggregator)
            config["test_id"] = idx
            config["description"] = (
                f"Test {idx}/20: "
                f"Semantic={semantic.value}, Aggregator={aggregator.value}"
            )
            configs.append(config)

        return configs

    def apply_config_to_state(
        self,
        state: Dict,
        config: Dict
    ) -> Dict:
        """
        설정을 GraphState에 적용

        Args:
            state: GraphState 딕셔너리
            config: 노드 설정

        Returns:
            수정된 state
        """
        # Thread 가중치 오버라이드
        state["thread_weights"] = config["thread_weights"]

        # 설정 메타데이터 추가
        state["test_config"] = {
            "combination_id": config["combination_id"],
            "test_id": config["test_id"],
            "semantic_expander": config["semantic_expander"]["active_type"],
            "aggregator": config["aggregator"]["active_type"]
        }

        return state


# 편의 함수들
def get_config_manager() -> ConfigManager:
    """ConfigManager 인스턴스 반환"""
    return ConfigManager()


def get_all_test_configs() -> List[Dict]:
    """모든 테스트 설정 반환 (20가지)"""
    manager = ConfigManager()
    return manager.generate_all_configs()


if __name__ == "__main__":
    # 테스트 코드
    manager = ConfigManager()
    configs = manager.generate_all_configs()

    print(f"총 {len(configs)}가지 조합 생성됨")
    print("\n처음 5가지 조합:")
    for config in configs[:5]:
        print(f"  - {config['description']}")
        print(f"    ID: {config['combination_id']}")
        print(f"    Thread Weights: {config['thread_weights']}")
        print()
