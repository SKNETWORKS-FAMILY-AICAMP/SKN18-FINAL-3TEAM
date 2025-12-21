"""
Configuration Manager for 80 Combination Testing

80가지 조합 자동 생성:
- 4가지 Semantic Expander: temporal, category, causal_chain, pgvector
- 5가지 Aggregator Thread: outgoing_relations, incoming_relations, entity_properties, connected_entities, type_and_summary
- 4가지 Entity Boost Mode: exact_match, partial_match, normalized_match, penalty_match

총 조합: 4 × 5 × 4 = 80가지
"""

from enum import Enum
from typing import Dict, List, Any, Iterator
from dataclasses import dataclass
import itertools


# =====================================================
# Enums for Test Dimensions
# =====================================================
class SemanticExpanderType(Enum):
    """Semantic Expander 타입 (4가지)"""
    TEMPORAL = "temporal"
    CATEGORY = "category"
    CAUSAL_CHAIN = "causal_chain"
    PGVECTOR = "pgvector"


class AggregatorThreadType(Enum):
    """Aggregator Thread 타입 (5가지)"""
    OUTGOING_RELATIONS = "outgoing_relations"
    INCOMING_RELATIONS = "incoming_relations"
    ENTITY_PROPERTIES = "entity_properties"
    CONNECTED_ENTITIES = "connected_entities"
    TYPE_AND_SUMMARY = "type_and_summary"


class EntityBoostMode(Enum):
    """Entity Boost Mode (4가지)"""
    EXACT_MATCH = "exact_match"          # 정확 매칭된 엔티티만
    PARTIAL_MATCH = "partial_match"      # 부분 매칭된 엔티티만
    NORMALIZED_MATCH = "normalized_match"  # 정규화 매칭된 엔티티만
    PENALTY_MATCH = "penalty_match"      # 매칭 안 된 엔티티만 (품질 비교용)


# =====================================================
# Test Configuration Dataclass
# =====================================================
@dataclass
class TestConfiguration:
    """단일 테스트 조합 설정"""
    combination_id: int  # 조합 번호 (1-80)
    semantic_expander: str  # temporal, category, causal_chain, pgvector
    aggregator_thread: str  # outgoing_relations, incoming_relations, ...
    entity_boost_mode: str  # exact_match, partial_match, normalized_match, penalty_match

    def to_test_config(self) -> Dict[str, Any]:
        """GraphState.test_config 형식으로 변환"""
        return {
            "semantic_expander": {
                "temporal": self.semantic_expander == "temporal",
                "category": self.semantic_expander == "category",
                "causal_chain": self.semantic_expander == "causal_chain",
                "pgvector": self.semantic_expander == "pgvector"
            },
            "aggregator_threads": {
                "outgoing_relations": self.aggregator_thread == "outgoing_relations",
                "incoming_relations": self.aggregator_thread == "incoming_relations",
                "entity_properties": self.aggregator_thread == "entity_properties",
                "connected_entities": self.aggregator_thread == "connected_entities",
                "type_and_summary": self.aggregator_thread == "type_and_summary"
            },
            "entity_boost_mode": self.entity_boost_mode
        }

    def get_description(self) -> str:
        """조합 설명 반환"""
        return f"#{self.combination_id}: {self.semantic_expander} + {self.aggregator_thread} + {self.entity_boost_mode}"

    def get_short_name(self) -> str:
        """짧은 이름 반환 (파일명 등에 사용)"""
        semantic_short = {
            "temporal": "temp",
            "category": "cat",
            "causal_chain": "causal",
            "pgvector": "vec"
        }
        thread_short = {
            "outgoing_relations": "out",
            "incoming_relations": "in",
            "entity_properties": "prop",
            "connected_entities": "conn",
            "type_and_summary": "type"
        }
        boost_short = {
            "exact_match": "exact",
            "partial_match": "partial",
            "normalized_match": "norm",
            "penalty_match": "penalty"
        }

        return f"{semantic_short[self.semantic_expander]}_{thread_short[self.aggregator_thread]}_{boost_short[self.entity_boost_mode]}"


# =====================================================
# Configuration Manager
# =====================================================
class ConfigurationManager:
    """80가지 테스트 조합 생성 및 관리"""

    def __init__(self):
        self.combinations: List[TestConfiguration] = []
        self._generate_all_combinations()

    def _generate_all_combinations(self):
        """80가지 조합 생성"""
        combination_id = 1

        for semantic in SemanticExpanderType:
            for thread in AggregatorThreadType:
                for boost in EntityBoostMode:
                    config = TestConfiguration(
                        combination_id=combination_id,
                        semantic_expander=semantic.value,
                        aggregator_thread=thread.value,
                        entity_boost_mode=boost.value
                    )
                    self.combinations.append(config)
                    combination_id += 1

    def get_all_combinations(self) -> List[TestConfiguration]:
        """모든 조합 반환"""
        return self.combinations

    def get_combination_by_id(self, combination_id: int) -> TestConfiguration:
        """ID로 조합 조회"""
        if 1 <= combination_id <= 80:
            return self.combinations[combination_id - 1]
        raise ValueError(f"Invalid combination_id: {combination_id}. Must be 1-80.")

    def get_combinations_by_semantic(self, semantic: str) -> List[TestConfiguration]:
        """특정 Semantic Expander로 필터링 (20가지)"""
        return [c for c in self.combinations if c.semantic_expander == semantic]

    def get_combinations_by_thread(self, thread: str) -> List[TestConfiguration]:
        """특정 Aggregator Thread로 필터링 (16가지)"""
        return [c for c in self.combinations if c.aggregator_thread == thread]

    def get_combinations_by_boost(self, boost: str) -> List[TestConfiguration]:
        """특정 Entity Boost Mode로 필터링 (20가지)"""
        return [c for c in self.combinations if c.entity_boost_mode == boost]

    def get_combinations_by_filters(
        self,
        semantic: str = None,
        thread: str = None,
        boost: str = None
    ) -> List[TestConfiguration]:
        """여러 조건으로 필터링"""
        filtered = self.combinations

        if semantic:
            filtered = [c for c in filtered if c.semantic_expander == semantic]
        if thread:
            filtered = [c for c in filtered if c.aggregator_thread == thread]
        if boost:
            filtered = [c for c in filtered if c.entity_boost_mode == boost]

        return filtered

    def iter_combinations(self) -> Iterator[TestConfiguration]:
        """조합 반복자 반환"""
        return iter(self.combinations)

    def get_summary(self) -> Dict[str, Any]:
        """조합 통계 요약"""
        return {
            "total_combinations": len(self.combinations),
            "semantic_expanders": len(SemanticExpanderType),
            "aggregator_threads": len(AggregatorThreadType),
            "entity_boost_modes": len(EntityBoostMode),
            "combinations_per_semantic": 20,  # 5 threads × 4 boosts
            "combinations_per_thread": 16,    # 4 semantics × 4 boosts
            "combinations_per_boost": 20      # 4 semantics × 5 threads
        }

    def print_all_combinations(self):
        """모든 조합 출력 (디버깅용)"""
        print("=" * 80)
        print(f"Total Combinations: {len(self.combinations)}")
        print("=" * 80)

        current_semantic = None
        for config in self.combinations:
            if config.semantic_expander != current_semantic:
                current_semantic = config.semantic_expander
                print(f"\n[{current_semantic.upper()}]")
                print("-" * 80)

            print(f"{config.combination_id:3d}. {config.get_description()}")

        print("\n" + "=" * 80)
        print(f"Summary: {self.get_summary()}")
        print("=" * 80)


# =====================================================
# Utility Functions
# =====================================================
def create_test_config(
    semantic_expander: str,
    aggregator_thread: str,
    entity_boost_mode: str
) -> Dict[str, Any]:
    """
    단일 조합의 test_config 생성

    Args:
        semantic_expander: temporal, category, causal_chain, pgvector
        aggregator_thread: outgoing_relations, incoming_relations, ...
        entity_boost_mode: exact_match, partial_match, normalized_match, penalty_match

    Returns:
        GraphState.test_config 형식의 딕셔너리
    """
    return {
        "semantic_expander": {
            "temporal": semantic_expander == "temporal",
            "category": semantic_expander == "category",
            "causal_chain": semantic_expander == "causal_chain",
            "pgvector": semantic_expander == "pgvector"
        },
        "aggregator_threads": {
            "outgoing_relations": aggregator_thread == "outgoing_relations",
            "incoming_relations": aggregator_thread == "incoming_relations",
            "entity_properties": aggregator_thread == "entity_properties",
            "connected_entities": aggregator_thread == "connected_entities",
            "type_and_summary": aggregator_thread == "type_and_summary"
        },
        "entity_boost_mode": entity_boost_mode
    }


def validate_test_config(test_config: Dict[str, Any]) -> bool:
    """
    test_config 유효성 검증

    Args:
        test_config: GraphState.test_config

    Returns:
        유효하면 True
    """
    try:
        # semantic_expander: 정확히 1개만 True여야 함
        semantic = test_config.get("semantic_expander", {})
        semantic_count = sum(1 for v in semantic.values() if v)
        if semantic_count != 1:
            print(f"[ERROR] semantic_expander must have exactly 1 True value, got {semantic_count}")
            return False

        # aggregator_threads: 정확히 1개만 True여야 함
        threads = test_config.get("aggregator_threads", {})
        thread_count = sum(1 for v in threads.values() if v)
        if thread_count != 1:
            print(f"[ERROR] aggregator_threads must have exactly 1 True value, got {thread_count}")
            return False

        # entity_boost_mode: 유효한 값이어야 함
        boost = test_config.get("entity_boost_mode")
        valid_boosts = ["exact_match", "partial_match", "normalized_match", "penalty_match"]
        if boost not in valid_boosts:
            print(f"[ERROR] entity_boost_mode must be one of {valid_boosts}, got {boost}")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] test_config validation failed: {e}")
        return False


# =====================================================
# Main (테스트용)
# =====================================================
if __name__ == "__main__":
    print("Testing ConfigurationManager...\n")

    # ConfigurationManager 생성
    manager = ConfigurationManager()

    # 모든 조합 출력
    manager.print_all_combinations()

    # 필터링 테스트
    print("\n" + "=" * 80)
    print("Filter Tests")
    print("=" * 80)

    print("\n1. Temporal semantic만 (20가지):")
    temporal_combos = manager.get_combinations_by_semantic("temporal")
    print(f"   Count: {len(temporal_combos)}")
    for c in temporal_combos[:3]:
        print(f"   - {c.get_description()}")
    print(f"   ... ({len(temporal_combos) - 3} more)")

    print("\n2. Outgoing_relations thread만 (16가지):")
    outgoing_combos = manager.get_combinations_by_thread("outgoing_relations")
    print(f"   Count: {len(outgoing_combos)}")
    for c in outgoing_combos[:3]:
        print(f"   - {c.get_description()}")
    print(f"   ... ({len(outgoing_combos) - 3} more)")

    print("\n3. Exact_match boost만 (20가지):")
    exact_combos = manager.get_combinations_by_boost("exact_match")
    print(f"   Count: {len(exact_combos)}")
    for c in exact_combos[:3]:
        print(f"   - {c.get_description()}")
    print(f"   ... ({len(exact_combos) - 3} more)")

    print("\n4. Temporal + Outgoing + Exact (1가지):")
    specific_combos = manager.get_combinations_by_filters(
        semantic="temporal",
        thread="outgoing_relations",
        boost="exact_match"
    )
    print(f"   Count: {len(specific_combos)}")
    for c in specific_combos:
        print(f"   - {c.get_description()}")
        print(f"     Short name: {c.get_short_name()}")
        print(f"     Test config: {c.to_test_config()}")

    # test_config 유효성 검증
    print("\n" + "=" * 80)
    print("Validation Tests")
    print("=" * 80)

    config1 = manager.get_combination_by_id(1)
    test_config1 = config1.to_test_config()
    print(f"\n1. Valid config (Combo #1): {validate_test_config(test_config1)}")

    invalid_config = {
        "semantic_expander": {
            "temporal": True,
            "category": True,  # 2개 True - 잘못됨
            "causal_chain": False,
            "pgvector": False
        },
        "aggregator_threads": {
            "outgoing_relations": True,
            "incoming_relations": False,
            "entity_properties": False,
            "connected_entities": False,
            "type_and_summary": False
        },
        "entity_boost_mode": "exact_match"
    }
    print(f"2. Invalid config (2 semantics True): {validate_test_config(invalid_config)}")

    print("\n" + "=" * 80)
    print("ConfigurationManager test completed successfully!")
    print("=" * 80)
