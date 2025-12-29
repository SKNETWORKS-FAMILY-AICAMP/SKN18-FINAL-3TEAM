"""
Evidence 점수 계산 유틸리티

실험 데이터 기반 (660개 케이스) + 쿼리 타입별 동적 가중치
- Isolation Study: 컴포넌트별 단독 성능 측정 (240개)
- Ablation Study: 컴포넌트 제거 시 영향 측정 (300개)
- Grid Search: 최적 조합 탐색 (120개)

설계 원칙:
1. 1점 만점 (0.0 ~ 1.0)
2. 컴포넌트별 Min-Max 정규화
3. 쿼리 타입별 동적 가중치 (config.py QUERY_TYPE_CONFIGS 기반)
4. 가중 평균 방식 (곱셈 대신)

최종 업데이트: 2024-12-29
"""

from typing import Dict

# ============================================================
# 1. 실험 데이터: Isolation Study 원본 성능
# ============================================================
# 출처: backend/ragas/ontology_evaluate/docs/experiment_docs/ISOLATION_EXPERIMENT_RESULTS.md
#
# ⭐ 핵심 변경: 쿼리 타입별 Component 점수 차별화
# - Semantic Expander: 쿼리 타입별로 성능이 극명하게 다름 (실험 데이터)
# - Thread Aggregator: 전역 점수 (쿼리 타입별 데이터 없음)
# - Entity Boost: 전역 점수 (쿼리 타입별 데이터 없음)

# ============================================================
# 1-1. Semantic Expander: 쿼리 타입별 점수 (실험 데이터)
# ============================================================
# 출처: ISOLATION_EXPERIMENT_RESULTS.md Lines 62-67
#
# 발견:
# - factual: causal_chain 0.7392 > temporal 0.7007 (+5.5%)
# - causal: temporal 0.6994 > causal_chain 0.6862 (+1.9%)
# - comparative: causal_chain 0.9104 >> temporal 0.6100 (+49.2% !!!)
# - deep_analysis: temporal 0.6768 > causal_chain 0.6442 (+5.1%)
#
# 중요: pgvector 데이터는 쿼리 타입별로 없음 → 전역 평균 사용

SEMANTIC_EXPANDER_BY_QUERY_TYPE = {
    "factual": {
        "causal_chain": 0.7392,   # 🥇 factual에 최적
        "temporal": 0.7007,       # 🥈
        "pgvector": 0.6402,       # 🥉 (실험 데이터)
        "none": 0.6705            # baseline 추정치 (전역 평균 사용)
    },
    "causal": {
        "temporal": 0.6994,       # 🥇 causal에 최적
        "causal_chain": 0.6862,   # 🥈
        "pgvector": 0.6789,       # 🥉 (실험 데이터)
        "none": 0.6705            # baseline
    },
    "comparative": {
        "causal_chain": 0.9104,   # 🥇 압도적 (+49.2%)
        "pgvector": 0.6456,       # 🥈 (실험 데이터)
        "temporal": 0.6100,       # 🥉
        "none": 0.6705            # baseline
    },
    "deep_analysis": {
        "temporal": 0.6768,       # 🥇 deep_analysis에 최적
        "pgvector": 0.6560,       # 🥈 (실험 데이터)
        "causal_chain": 0.6442,   # 🥉
        "none": 0.6705            # baseline
    }
}

# ============================================================
# 1-2. Thread Aggregator: 쿼리 타입별 점수 (실험 데이터)
# ============================================================
# 출처: backend/ragas/ontology_evaluate/data/results_isolation/thread_isolation_summary.json
#
# ⭐ 핵심 발견: Thread도 쿼리 타입별로 성능이 다름
# - factual: type_and_summary 1위 (0.8264)
# - causal: type_and_summary 1위 (0.9480)
# - comparative: entity_properties 1위 (0.8662) ⭐ type_and_summary가 아님!
# - deep_analysis: outgoing_relations 1위 (0.9828) ⭐ 전역 평균과 정반대!

THREAD_AGGREGATOR_BY_QUERY_TYPE = {
    "factual": {
        "type_and_summary": 0.8264,      # 🥇 1위
        "entity_properties": 0.8159,     # 🥈 2위
        "incoming_relations": 0.7938,    # 3위
        "connected_entities": 0.7829,    # 4위
        "outgoing_relations": 0.7590,    # 5위
    },
    "causal": {
        "type_and_summary": 0.9480,      # 🥇 1위 (압도적)
        "entity_properties": 0.8976,     # 🥈 2위
        "connected_entities": 0.8874,    # 3위
        "outgoing_relations": 0.8521,    # 4위
        "incoming_relations": 0.7253,    # 5위 (최하위)
    },
    "comparative": {
        "entity_properties": 0.8662,     # 🥇 1위 ⭐ type_and_summary가 아님!
        "type_and_summary": 0.8596,      # 🥈 2위
        "incoming_relations": 0.8188,    # 3위
        "connected_entities": 0.7927,    # 4위
        "outgoing_relations": 0.7773,    # 5위
    },
    "deep_analysis": {
        "outgoing_relations": 0.9828,    # 🥇 1위 ⭐ 전역 평균과 정반대!
        "entity_properties": 0.9709,     # 🥈 2위
        "type_and_summary": 0.9632,      # 🥉 3위
        "connected_entities": 0.9332,    # 4위
        "incoming_relations": 0.8830,    # 5위
    },
}

# 전역 평균 (하위 호환성)
THREAD_AGGREGATOR_GLOBAL = {
    "type_and_summary": 0.7984,
    "entity_properties": 0.7389,
    "outgoing_relations": 0.7115,
    "incoming_relations": 0.6910,
    "connected_entities": 0.6220
}

# ============================================================
# 1-3. Entity Boost: 쿼리 타입별 점수 (실험 데이터)
# ============================================================
# 출처: backend/ragas/ontology_evaluate/data/results_isolation/entity_boost_isolation_summary.json
#
# ⭐ 핵심 발견: Entity Boost도 쿼리 타입별로 성능이 다름
# - factual: normalized 1위 (0.8162)
# - causal: none 1위 (0.9351) ⭐ boost 없음이 최고!
# - comparative: none 1위 (0.8613) ⭐ boost 없음이 최고!
# - deep_analysis: partial 1위 (1.0034)

ENTITY_BOOST_BY_QUERY_TYPE = {
    "factual": {
        "normalized": 0.8162,    # 🥇 1위
        "exact": 0.8159,         # 🥈 2위 (근소한 차이)
        "partial": 0.8033,       # 3위
        "none": 0.8027,          # 4위
    },
    "causal": {
        "none": 0.9351,          # 🥇 1위 ⭐ boost 없음이 최고!
        "normalized": 0.9216,    # 🥈 2위
        "partial": 0.8966,       # 3위
        "exact": 0.8799,         # 4위
    },
    "comparative": {
        "none": 0.8613,          # 🥇 1위 ⭐ boost 없음이 최고!
        "exact": 0.8226,         # 🥈 2위
        "partial": 0.8049,       # 3위
        "normalized": 0.7918,    # 4위
    },
    "deep_analysis": {
        "partial": 1.0034,       # 🥇 1위 ⭐ 1.0 초과!
        "normalized": 0.9930,    # 🥈 2위
        "none": 0.9895,          # 🥉 3위
        "exact": 0.9370,         # 4위
    },
}

# 전역 평균 (하위 호환성)
ENTITY_BOOST_GLOBAL = {
    "none": 0.7634,
    "normalized": 0.7593,
    "partial": 0.7516,
    "exact": 0.7399
}

# ============================================================
# 하위 호환성: 전역 평균 (기존 코드와의 호환)
# ============================================================
ISOLATION_RAW_PERFORMANCE = {
    "semantic_expander": {
        # 전역 평균 (4개 쿼리 타입 평균)
        "causal_chain": 0.7611,   # 전체 평균 (실험 전체)
        "pgvector": 0.7451,
        "temporal": 0.7350,
        "none": 0.6705
    },
    "thread_aggregator": THREAD_AGGREGATOR_GLOBAL,
    "entity_boost": ENTITY_BOOST_GLOBAL
}


def _normalize_within_component(raw_score: float, component_name: str, query_type: str = None) -> float:
    """
    컴포넌트 내 Min-Max 정규화 (⭐ 쿼리 타입별)

    목적: "특목고 10등"과 "시골학교 10등" 구분
    - causal_chain의 0.6점과 pgvector의 0.6점은 다른 의미
    - **factual 쿼리의 causal_chain과 causal 쿼리의 causal_chain도 다른 의미**
    - 각 (컴포넌트 × 쿼리 타입) 내에서 상대적 성능을 0~1로 정규화

    Args:
        raw_score: 원본 절대 성능 (0.6, 0.7 등)
        component_name: "semantic_expander" | "thread_aggregator" | "entity_boost"
        query_type: "factual" | "causal" | "comparative" | "deep_analysis" (Semantic Expander에만 사용)

    Returns:
        0~1 정규화된 점수

    Example - factual 쿼리의 Semantic Expander:
        >>> # factual: [none 0.6705, temporal 0.7007, pgvector 0.6402, causal_chain 0.7392]
        >>> # Range: 0.6402 ~ 0.7392
        >>> _normalize_within_component(0.7392, "semantic_expander", "factual")
        1.0  # factual의 최고 (causal_chain) → 1.0

        >>> _normalize_within_component(0.6402, "semantic_expander", "factual")
        0.0  # factual의 최저 (pgvector) → 0.0

    Example - comparative 쿼리의 Semantic Expander:
        >>> # comparative: [temporal 0.6100, pgvector 0.6456, none 0.6705, causal_chain 0.9104]
        >>> # Range: 0.6100 ~ 0.9104
        >>> _normalize_within_component(0.9104, "semantic_expander", "comparative")
        1.0  # comparative의 최고 (causal_chain 압도적) → 1.0

        >>> _normalize_within_component(0.6100, "semantic_expander", "comparative")
        0.0  # comparative의 최저 (temporal) → 0.0
    """
    # ⭐ 모든 Component: 쿼리 타입별 정규화
    if component_name == "semantic_expander" and query_type:
        if query_type in SEMANTIC_EXPANDER_BY_QUERY_TYPE:
            scores = list(SEMANTIC_EXPANDER_BY_QUERY_TYPE[query_type].values())
        else:
            # fallback: 전역 평균
            scores = list(ISOLATION_RAW_PERFORMANCE["semantic_expander"].values())
    elif component_name == "thread_aggregator" and query_type:
        if query_type in THREAD_AGGREGATOR_BY_QUERY_TYPE:
            scores = list(THREAD_AGGREGATOR_BY_QUERY_TYPE[query_type].values())
        else:
            # fallback: 전역 평균
            scores = list(THREAD_AGGREGATOR_GLOBAL.values())
    elif component_name == "entity_boost" and query_type:
        if query_type in ENTITY_BOOST_BY_QUERY_TYPE:
            scores = list(ENTITY_BOOST_BY_QUERY_TYPE[query_type].values())
        else:
            # fallback: 전역 평균
            scores = list(ENTITY_BOOST_GLOBAL.values())
    # fallback (query_type 없을 때)
    elif component_name == "thread_aggregator":
        scores = list(THREAD_AGGREGATOR_GLOBAL.values())
    elif component_name == "entity_boost":
        scores = list(ENTITY_BOOST_GLOBAL.values())
    else:
        # fallback
        scores = list(ISOLATION_RAW_PERFORMANCE[component_name].values())

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return 1.0

    return (raw_score - min_score) / (max_score - min_score)


# ============================================================
# 2. 정규화된 성능 점수 (쿼리 타입별)
# ============================================================
# ⭐ 핵심: 모든 Component를 쿼리 타입별로 정규화

# 2-1. Semantic Expander: 쿼리 타입별 정규화
NORMALIZED_SEMANTIC_BY_QUERY_TYPE = {
    query_type: {
        method: _normalize_within_component(score, "semantic_expander", query_type)
        for method, score in scores_dict.items()
    }
    for query_type, scores_dict in SEMANTIC_EXPANDER_BY_QUERY_TYPE.items()
}

# 2-2. Thread Aggregator: 쿼리 타입별 정규화
NORMALIZED_THREAD_BY_QUERY_TYPE = {
    query_type: {
        thread: _normalize_within_component(score, "thread_aggregator", query_type)
        for thread, score in scores_dict.items()
    }
    for query_type, scores_dict in THREAD_AGGREGATOR_BY_QUERY_TYPE.items()
}

# 2-3. Entity Boost: 쿼리 타입별 정규화
NORMALIZED_BOOST_BY_QUERY_TYPE = {
    query_type: {
        boost: _normalize_within_component(score, "entity_boost", query_type)
        for boost, score in scores_dict.items()
    }
    for query_type, scores_dict in ENTITY_BOOST_BY_QUERY_TYPE.items()
}

# 전역 정규화 (하위 호환성)
NORMALIZED_THREAD_GLOBAL = {
    thread: _normalize_within_component(score, "thread_aggregator")
    for thread, score in THREAD_AGGREGATOR_GLOBAL.items()
}

NORMALIZED_BOOST_GLOBAL = {
    boost: _normalize_within_component(score, "entity_boost")
    for boost, score in ENTITY_BOOST_GLOBAL.items()
}

# ============================================================
# 하위 호환성: 전역 평균 정규화 (기존 코드)
# ============================================================
NORMALIZED_PERFORMANCE = {
    "semantic_expander": {
        method: _normalize_within_component(score, "semantic_expander")
        for method, score in ISOLATION_RAW_PERFORMANCE["semantic_expander"].items()
    },
    "thread_aggregator": NORMALIZED_THREAD_GLOBAL,
    "entity_boost": NORMALIZED_BOOST_GLOBAL
}

# ============================================================
# 2. 쿼리 타입별 컴포넌트 중요도 (config.py 기반 계산)
# ============================================================
# 출처: backend/langgraph_fuseki/config.py:99-164 QUERY_TYPE_CONFIGS
#
# 계산 방법:
# 1. config.py의 thread_weights 합계 계산
# 2. semantic_expander 활성화 여부로 중요도 추정
# 3. entity_boost 설정으로 중요도 추정
#
# factual:
#   - semantic: 모두 False → 중요도 낮음 (0.10)
#   - thread: outgoing=0, 나머지=1.0 (4개) → 중요도 높음 (0.60)
#   - boost: normalized → 중요도 중간 (0.30)
#
# causal:
#   - semantic: causal_chain만 True → 중요도 중간-상 (0.35)
#   - thread: outgoing=1.0, incoming=0, 나머지=1.0 (4개) → 중요도 중간 (0.45)
#   - boost: partial → 중요도 낮음 (0.20)
#
# comparative:
#   - semantic: 모두 False → 중요도 매우 낮음 (0.05)
#   - thread: outgoing=0, 나머지=1.0 (4개) → 중요도 매우 높음 (0.65)
#   - boost: normalized → 중요도 중간 (0.30)
#
# deep_analysis:
#   - semantic: temporal + causal 모두 True → 중요도 높음 (0.40)
#   - thread: outgoing=1.0, incoming=0, 나머지=1.0 (4개) → 중요도 중간 (0.40)
#   - boost: partial → 중요도 낮음 (0.20)

COMPONENT_IMPORTANCE_BY_QUERY_TYPE = {
    "factual": {
        # 정확한 단답형 → Thread가 가장 중요, 확장 최소화
        # config: semantic 모두 False, thread 4개 활성화, boost=normalized
        "thread": 0.60,      # 60% - 정확한 속성/요약 정보 핵심
        "semantic": 0.10,    # 10% - 확장 최소화 (Intent Drift 방지)
        "boost": 0.30        # 30% - Entity 정확성 중요
    },
    "causal": {
        # 인과관계 → Semantic과 Thread 균형
        # config: causal_chain만 True, thread 4개, boost=partial
        "thread": 0.45,      # 45% - outgoing_relations 중요
        "semantic": 0.35,    # 35% - causal_chain 확장 필요 (+0.23 향상)
        "boost": 0.20        # 20% - partial 매칭 허용
    },
    "comparative": {
        # 비교 → Thread 구조 매우 중요
        # config: semantic 모두 False, thread 4개, boost=normalized
        "thread": 0.65,      # 65% - 관계 구조 유지 (outgoing=0으로 -0.38 방지)
        "semantic": 0.05,    # 5% - 확장 거의 불필요
        "boost": 0.30        # 30% - 정확한 매칭
    },
    "deep_analysis": {
        # 심층 분석 → Semantic 확장 중요
        # config: temporal + causal 모두 True, thread 4개, boost=partial
        "thread": 0.40,      # 40%
        "semantic": 0.40,    # 40% - 폭넓은 맥락 (evidence_diversity 0.16)
        "boost": 0.20        # 20%
    }
}

# ============================================================
# 3. Evidence 점수 계산 함수
# ============================================================

def calculate_evidence_score(
    evidence_metadata: Dict,
    query_type: str = "factual",
    use_query_type_aware: bool = True  # True: v3.0 (쿼리 타입별), False: Baseline (전역 평균)
) -> float:
    """
    실험 데이터 기반 Evidence 점수 계산 (1점 만점)

    ⭐ 핵심 변경: 쿼리 타입별 Semantic Expander 점수 차별화
    - factual 쿼리의 causal_chain: 1.0 (최고)
    - causal 쿼리의 causal_chain: 0.44 (3위)
    - comparative 쿼리의 causal_chain: 1.0 (압도적)

    ⭐ 확장 방법 내 세부 점수 반영:
    - causal_chain: hop_count에 따라 감쇠 (1-hop: 1.0, 2-hop: 0.9, 3-hop: 0.81)
    - temporal: year_distance에 따라 감쇠 (0년: 1.0, 10년: 0.5, 20년+: 0.0)
    - pgvector: similarity에 따라 점수 (유사도 × 가중치)

    Args:
        evidence_metadata: Evidence 메타데이터
            {
                "expansion_method": "causal_chain" | "temporal" | "pgvector" | "none",
                "thread_type": "type_and_summary" | "entity_properties" | ...,
                "entity_match_type": "exact" | "partial" | "normalized" | "none",
                "hop_count": int (causal_chain용, 선택),
                "year_distance": int (temporal용, 선택),
                "pgvector_similarity": float (pgvector용, 선택),
                "relevance_score": float (이미 계산된 점수, 선택)
            }
        query_type: "factual" | "causal" | "comparative" | "deep_analysis"

    Returns:
        0.0 ~ 1.0 범위의 점수

    Example - factual 쿼리 + causal_chain (1-hop):
        >>> metadata = {
        ...     "expansion_method": "causal_chain",
        ...     "hop_count": 1,  # 1-hop: 최고 점수
        ...     "thread_type": "type_and_summary",
        ...     "entity_match_type": "normalized"
        ... }
        >>> calculate_evidence_score(metadata, query_type="factual")
        0.849  # 1.0×0.10 + 1.0×0.60 + 0.83×0.30 = 0.849

    Example - causal 쿼리 + causal_chain (3-hop, 감쇠 적용):
        >>> metadata = {
        ...     "expansion_method": "causal_chain",
        ...     "hop_count": 3,  # 3-hop: 0.81 감쇠
        ...     "thread_type": "type_and_summary",
        ...     "entity_match_type": "normalized"
        ... }
        >>> calculate_evidence_score(metadata, query_type="causal")
        0.770  # (0.44 × 0.81)×0.35 + 1.0×0.45 + 0.83×0.20 = 0.770
    """

    # 1. 쿼리 타입별 정규화된 성능 점수 가져오기
    expansion_method = evidence_metadata.get("expansion_method", "none")
    thread_type = evidence_metadata.get("thread_type")
    entity_match_type = evidence_metadata.get("entity_match_type", "none")

    # ⭐ Semantic Expander: Baseline vs v3.0 구분
    if use_query_type_aware and query_type in NORMALIZED_SEMANTIC_BY_QUERY_TYPE:
        # v3.0: 쿼리 타입별 점수 사용
        base_semantic_score = NORMALIZED_SEMANTIC_BY_QUERY_TYPE[query_type].get(
            expansion_method,
            0.0  # baseline (확장 없음)
        )
    else:
        # Baseline: 전역 평균 점수 사용 (Quick Win 실험 당시 점수)
        base_semantic_score = NORMALIZED_PERFORMANCE["semantic_expander"].get(
            expansion_method,
            0.0
        )

    # ⭐ 확장 방법 내 세부 점수 적용 (hop_count, year_distance, similarity)
    detail_factor = 1.0  # 기본값 (세부 정보 없으면 1.0)
    
    if expansion_method == "causal_chain":
        hop_count = evidence_metadata.get("hop_count")
        if hop_count is not None:
            # hop이 적을수록 높은 점수 (1-hop: 1.0, 2-hop: 0.9, 3-hop: 0.81)
            detail_factor = 0.9 ** (hop_count - 1)
    
    elif expansion_method == "temporal":
        year_distance = evidence_metadata.get("year_distance")
        if year_distance is not None:
            # 연도 거리가 가까울수록 높은 점수 (0년: 1.0, 10년: 0.5, 20년+: 0.0)
            detail_factor = max(0.0, 1.0 - (year_distance / 20.0))
    
    elif expansion_method == "pgvector":
        similarity = evidence_metadata.get("pgvector_similarity") or evidence_metadata.get("similarity")
        if similarity is not None:
            # 벡터 유사도 직접 사용
            detail_factor = similarity
    
    # 이미 계산된 relevance_score가 있으면 사용 (세부 점수 반영된 값)
    relevance_score = evidence_metadata.get("relevance_score")
    if relevance_score is not None and expansion_method != "none":
        # relevance_score는 이미 세부 점수가 반영된 값이므로, 이를 base_semantic_score에 반영
        # base_semantic_score는 정규화된 점수(0-1)이고, relevance_score도 0-1 범위
        # 두 값을 결합: base_semantic_score의 세부 조정
        semantic_score = base_semantic_score * (relevance_score / 1.0)  # relevance_score를 비율로 사용
    else:
        # detail_factor를 base_semantic_score에 적용
        semantic_score = base_semantic_score * detail_factor

    # ⭐ Thread Aggregator: Baseline vs v3.0 구분
    if use_query_type_aware and query_type in NORMALIZED_THREAD_BY_QUERY_TYPE:
        # v3.0: 쿼리 타입별 점수 사용
        thread_score = NORMALIZED_THREAD_BY_QUERY_TYPE[query_type].get(
            thread_type,
            0.5  # 평균값 (정보 없을 때)
        )
    else:
        # Baseline: 전역 평균 점수 사용
        thread_score = NORMALIZED_THREAD_GLOBAL.get(
            thread_type,
            0.5
        )

    # ⭐ Entity Boost: Baseline vs v3.0 구분
    if use_query_type_aware and query_type in NORMALIZED_BOOST_BY_QUERY_TYPE:
        # v3.0: 쿼리 타입별 점수 사용
        boost_score = NORMALIZED_BOOST_BY_QUERY_TYPE[query_type].get(
            entity_match_type,
            0.5  # 평균값 (정보 없을 때)
        )
    else:
        # Baseline: 전역 평균 점수 사용
        boost_score = NORMALIZED_BOOST_GLOBAL.get(
            entity_match_type,
            1.0  # none (boost 없음, 전역에서는 1.0이 최고)
        )

    # 2. 쿼리 타입별 중요도 가져오기
    importance = COMPONENT_IMPORTANCE_BY_QUERY_TYPE.get(
        query_type,
        COMPONENT_IMPORTANCE_BY_QUERY_TYPE["factual"]  # 기본값
    )

    # 3. 가중 평균 계산
    final_score = (
        semantic_score * importance["semantic"] +
        thread_score * importance["thread"] +
        boost_score * importance["boost"]
    )

    return final_score


def calculate_query_evidence_fit(
    evidence_metadata: Dict,
    query_metadata: Dict
) -> float:
    """
    Evidence와 Query의 적합도 점수 (0~1)

    현재 시스템의 SPARQL 연결 분석과 Entity Matching 반영

    Args:
        evidence_metadata: Evidence 정보
            {
                "entity_match_type": "exact" | "partial" | "normalized" | "none",
                "connected_keyword_count": 2  # SPARQL로 발견된 키워드 수
            }
        query_metadata: Query 정보
            {
                "keywords": ["세조", "즉위"],
                "query_type": "causal"
            }

    Returns:
        0.0 ~ 1.0 범위의 적합도 점수

    Example:
        >>> evidence_meta = {
        ...     "entity_match_type": "exact",
        ...     "connected_keyword_count": 2
        ... }
        >>> query_meta = {
        ...     "keywords": ["세조", "즉위"],
        ...     "query_type": "causal"
        ... }
        >>> calculate_query_evidence_fit(evidence_meta, query_meta)
        1.0  # 0.5 (exact) + 0.5 (SPARQL 2/2) = 1.0
    """

    fit_score = 0.0

    # 1. Entity Matching (0~0.5)
    entity_match_type = evidence_metadata.get("entity_match_type")
    if entity_match_type == "exact":
        fit_score += 0.5
    elif entity_match_type == "normalized":
        fit_score += 0.4
    elif entity_match_type == "partial":
        fit_score += 0.3
    # else: +0.0 (none)

    # 2. SPARQL 연결 분석 (0~0.5)
    connected_keywords = evidence_metadata.get("connected_keyword_count", 0)
    total_keywords = len(query_metadata.get("keywords", []))
    if total_keywords > 0:
        keyword_match_ratio = min(connected_keywords / total_keywords, 1.0)
        fit_score += keyword_match_ratio * 0.5

    return min(fit_score, 1.0)


def calculate_final_evidence_score(
    evidence_metadata: Dict,
    query_metadata: Dict,
    base_weight: float = 0.8,
    fit_weight: float = 0.2,
    use_query_type_aware: bool = True  # True: v3.0, False: Baseline
) -> float:
    """
    최종 Evidence 점수 (1점 만점)

    기본 성능 점수(실험 기반)와 적합도 점수(Query 매칭)를 결합

    Args:
        evidence_metadata: Evidence 메타데이터
        query_metadata: Query 메타데이터
        base_weight: 기본 성능 가중치 (기본: 0.8)
        fit_weight: 적합도 가중치 (기본: 0.2)

    Returns:
        0.0 ~ 1.0 범위의 최종 점수

    Example - causal 쿼리의 최적 Evidence:
        >>> evidence_meta = {
        ...     "expansion_method": "causal_chain",
        ...     "thread_type": "outgoing_relations",
        ...     "entity_match_type": "exact",
        ...     "connected_keyword_count": 2
        ... }
        >>> query_meta = {
        ...     "keywords": ["임진왜란", "원인"],
        ...     "query_type": "causal"
        ... }
        >>> calculate_final_evidence_score(evidence_meta, query_meta)
        0.7436  # (0.6795 × 0.8) + (1.0 × 0.2) = 0.7436
        # 해석: 74.36% 품질 - causal 쿼리에 적합한 고품질 Evidence

    Example - factual 쿼리에 causal 확장 사용한 경우 (차선):
        >>> evidence_meta = {
        ...     "expansion_method": "causal_chain",      # factual에는 불필요
        ...     "thread_type": "outgoing_relations",
        ...     "entity_match_type": "partial",
        ...     "connected_keyword_count": 0
        ... }
        >>> query_meta = {
        ...     "keywords": ["세종대왕", "재위기간"],
        ...     "query_type": "factual"
        ... }
        >>> calculate_final_evidence_score(evidence_meta, query_meta)
        0.52  # (0.52 × 0.8) + (0.3 × 0.2) = 0.476
        # 해석: 47.6% 품질 - factual에 부적합 (불필요한 확장 + outgoing)
    """

    # 1. 기본 점수 (실험 데이터 기반)
    base_score = calculate_evidence_score(
        evidence_metadata,
        query_type=query_metadata.get("query_type", "factual"),
        use_query_type_aware=use_query_type_aware
    )

    # 2. 적합도 점수 (Query-Evidence 매칭)
    fit_score = calculate_query_evidence_fit(evidence_metadata, query_metadata)

    # 3. 가중 평균
    final_score = base_score * base_weight + fit_score * fit_weight

    return final_score


# ============================================================
# 4. 디버깅 및 설명 함수
# ============================================================

def explain_evidence_score(
    evidence_metadata: Dict,
    query_metadata: Dict
) -> Dict:
    """
    Evidence 점수 계산 과정을 상세히 설명

    Args:
        evidence_metadata: Evidence 메타데이터
        query_metadata: Query 메타데이터

    Returns:
        계산 과정 설명 딕셔너리

    Example:
        >>> evidence_meta = {
        ...     "expansion_method": "causal_chain",
        ...     "thread_type": "type_and_summary",
        ...     "entity_match_type": "exact"
        ... }
        >>> query_meta = {"query_type": "causal", "keywords": ["세조"]}
        >>> explain_evidence_score(evidence_meta, query_meta)
        {
            "query_type": "causal",
            "component_scores": {
                "semantic": {"raw": 0.7611, "normalized": 1.0, "weight": 0.35},
                "thread": {"raw": 0.7984, "normalized": 1.0, "weight": 0.45},
                "boost": {"raw": 0.7399, "normalized": 0.0, "weight": 0.20}
            },
            "base_score": 0.7950,
            "fit_score": 0.5,
            "final_score": 0.7360,
            "interpretation": "73.60% 품질 - causal 쿼리에 적합한 고품질 Evidence"
        }
    """
    query_type = query_metadata.get("query_type", "factual")
    expansion_method = evidence_metadata.get("expansion_method", "none")
    thread_type = evidence_metadata.get("thread_type")
    entity_match_type = evidence_metadata.get("entity_match_type", "none")

    # ⭐ 원본 점수 (쿼리 타입별)
    # Semantic: 쿼리 타입별 점수
    if query_type in SEMANTIC_EXPANDER_BY_QUERY_TYPE:
        semantic_raw = SEMANTIC_EXPANDER_BY_QUERY_TYPE[query_type].get(expansion_method, 0.6705)
    else:
        semantic_raw = ISOLATION_RAW_PERFORMANCE["semantic_expander"].get(expansion_method, 0.6705)

    # Thread: 쿼리 타입별 점수
    if query_type in THREAD_AGGREGATOR_BY_QUERY_TYPE:
        thread_raw = THREAD_AGGREGATOR_BY_QUERY_TYPE[query_type].get(thread_type, 0.7)
    else:
        thread_raw = THREAD_AGGREGATOR_GLOBAL.get(thread_type, 0.7)

    # Boost: 쿼리 타입별 점수
    if query_type in ENTITY_BOOST_BY_QUERY_TYPE:
        boost_raw = ENTITY_BOOST_BY_QUERY_TYPE[query_type].get(entity_match_type, 0.7634)
    else:
        boost_raw = ENTITY_BOOST_GLOBAL.get(entity_match_type, 0.7634)

    # ⭐ 정규화된 점수 (쿼리 타입별)
    # Semantic: 쿼리 타입별 정규화
    if query_type in NORMALIZED_SEMANTIC_BY_QUERY_TYPE:
        semantic_norm = NORMALIZED_SEMANTIC_BY_QUERY_TYPE[query_type].get(expansion_method, 0.0)
    else:
        semantic_norm = NORMALIZED_PERFORMANCE["semantic_expander"].get(expansion_method, 0.0)

    # Thread: 쿼리 타입별 정규화
    if query_type in NORMALIZED_THREAD_BY_QUERY_TYPE:
        thread_norm = NORMALIZED_THREAD_BY_QUERY_TYPE[query_type].get(thread_type, 0.5)
    else:
        thread_norm = NORMALIZED_THREAD_GLOBAL.get(thread_type, 0.5)

    # Boost: 쿼리 타입별 정규화
    if query_type in NORMALIZED_BOOST_BY_QUERY_TYPE:
        boost_norm = NORMALIZED_BOOST_BY_QUERY_TYPE[query_type].get(entity_match_type, 0.5)
    else:
        boost_norm = NORMALIZED_BOOST_GLOBAL.get(entity_match_type, 1.0)

    # 가중치
    importance = COMPONENT_IMPORTANCE_BY_QUERY_TYPE.get(query_type, COMPONENT_IMPORTANCE_BY_QUERY_TYPE["factual"])

    # 계산
    base_score = calculate_evidence_score(evidence_metadata, query_type)
    fit_score = calculate_query_evidence_fit(evidence_metadata, query_metadata)
    final_score = calculate_final_evidence_score(evidence_metadata, query_metadata)

    # 해석
    if final_score >= 0.8:
        interpretation = f"{final_score*100:.2f}% 품질 - {query_type} 쿼리에 최적의 고품질 Evidence"
    elif final_score >= 0.65:
        interpretation = f"{final_score*100:.2f}% 품질 - {query_type} 쿼리에 적합한 중상위 Evidence"
    elif final_score >= 0.5:
        interpretation = f"{final_score*100:.2f}% 품질 - {query_type} 쿼리에 사용 가능한 중하위 Evidence"
    else:
        interpretation = f"{final_score*100:.2f}% 품질 - {query_type} 쿼리에 부적합한 저품질 Evidence"

    return {
        "query_type": query_type,
        "component_scores": {
            "semantic": {
                "method": expansion_method,
                "raw": semantic_raw,
                "normalized": semantic_norm,
                "weight": importance["semantic"],
                "contribution": semantic_norm * importance["semantic"]
            },
            "thread": {
                "type": thread_type,
                "raw": thread_raw,
                "normalized": thread_norm,
                "weight": importance["thread"],
                "contribution": thread_norm * importance["thread"]
            },
            "boost": {
                "match_type": entity_match_type,
                "raw": boost_raw,
                "normalized": boost_norm,
                "weight": importance["boost"],
                "contribution": boost_norm * importance["boost"]
            }
        },
        "base_score": base_score,
        "fit_score": fit_score,
        "final_score": final_score,
        "interpretation": interpretation
    }
