"""
온톨로지 스키마 정의 (정적)

TODO: 추후 OWL 설계가 완료되면 SPARQL 기반 동적 조회로 교체
"""

from typing import Dict, List

# 온톨로지 클래스 및 속성 매핑
ONTOLOGY_SCHEMA: Dict[str, Dict[str, List[str]]] = {
    # 인물 (Person)
    "Person": {
        "properties": [
            # 기본 정보
            "hist:hasAlias",            # 별칭 (충무공, 李舜臣 등)
            "hist:hasBirthYear",        # 출생년도
            "hist:hasDeathYear",        # 사망년도
            "hist:bornIn",              # 출생지 (장소)
            "hist:diedIn",              # 사망지 (장소)

            # 활동
            "hist:participatesIn",      # 참여하다 (사건)
            "hist:hasRole",             # 역할을 갖다
            "hist:hasRank",             # 직위를 갖다
            "hist:commands",            # 지휘하다
            "hist:servesIn",            # 복무하다
            "hist:affiliatedWith",      # 소속되다 (국가)

            # 학문/문헌/교육 관련
            "hist:authored",            # 저술하다 (문헌)
            "hist:compiled",            # 편찬하다 (문헌)
            "hist:teacherOf",           # 스승이다
            "hist:studentOf",           # 제자이다
            "hist:servedUnder",         # 섬기다 (군주)
            "hist:hasField",            # 학문 분야
            "hist:founded",             # 설립하다 (기관)
            "hist:reformed",            # 개혁하다 (제도)

            # 분석용 (비하인드 스토리, 인물 분석)
            "hist:hasMotive",           # 동기
            "hist:hasAchievement",      # 업적
            "hist:hasRelationship",     # 인간관계

            # 시간 추론 결과 (Stage 4)
            "hist:contemporaryWith",    # [추론] 동시대 인물
            "hist:seniorTo",            # [추론] 선배
            "hist:juniorTo",            # [추론] 후배
            "hist:differentGenerationFrom",  # [추론] 다른 세대
            "hist:aliveDuring",         # [추론] ~시기에 생존
            "hist:hasLifespan",         # [추론] 수명 (연) - data property
            "hist:ageAt",               # [추론] 특정 사건 발생 시 나이 - data property

            # 인물 추론 결과 (Stage 1, 3)
            "hist:hasRelationshipWith", # [추론] 동료 관계
            "hist:hasEnemyRelationship",# [추론] 적대 관계
            "hist:hasLocalTies",        # [추론] 지역 연고
            "hist:causeOfDeath",        # [추론] 사망 원인 - data property
            "hist:hasInfluence",        # [추론] 영향력 - data property
            "hist:hasResponsibility",   # [추론] 책임 - data property
            "hist:hasLoyalty",          # [추론] 충성도 - data property

            # 인과관계 추론 결과 (Stage 2)
            "hist:hasStrategicAdvantage", # [추론] 전략적 우위 - data property

            # 패턴 추론 결과 (Stage 5)
            "hist:hasStrategyPattern",  # [추론] 전략 패턴 - data property
            "hist:hasWinningStreak",    # [추론] 연승 패턴 - data property
            "hist:hasComebackPattern",  # [추론] 역전 패턴 - data property
        ],
        "inverse_properties": [
            "hist:hasParticipant",      # 참여자를 갖다
            "hist:hasCommander",        # 지휘관을 갖다
        ]
    },

    # 사건 (Event)
    "Event": {
        "properties": [
            # 기본 정보
            "hist:hasDate",             # 날짜를 갖다
            "hist:hasYear",             # 연도를 갖다
            "hist:occursAt",            # 발생하다 (장소)
            "hist:hasParticipant",      # 참여자를 갖다
            "hist:hasCommander",        # 지휘관을 갖다

            # 인과관계 (What-if 추론용)
            "hist:leadsTo",             # ~로 이어지다 (결과)
            "hist:causedBy",            # ~에 의해 발생하다 (원인)
            "hist:hasPrecondition",     # 선행 조건
            "hist:hasImpact",           # 영향/파급효과
            "hist:hasOutcome",          # 결과

            # 맥락 (시대배경 분석용)
            "hist:partOf",              # ~의 일부이다 (상위 사건)
            "hist:hasContext",          # 시대적 맥락
            "hist:involves",            # 포함하다 (국가/인물)

            # 시간 추론 결과 (Stage 4)
            "hist:occursBefore",        # [추론] ~보다 먼저 발생
            "hist:occursAfter",         # [추론] ~보다 나중에 발생
            "hist:simultaneousWith",    # [추론] 동일 시기 사건
            "hist:followedBy",          # [추론] 다음 사건
            "hist:precededBy",          # [추론] 이전 사건
            "hist:hasDuration",         # [추론] 지속 기간 (연) - data property
            "hist:belongsToPeriod",     # [추론] 역사적 시대 - data property
            "hist:warType",             # [추론] 전쟁 유형 - data property

            # 인과관계 추론 결과 (Stage 2)
            "hist:indirectlyCausedBy",  # [추론] 간접적 인과관계

            # 패턴 추론 결과 (Stage 5)
            "hist:hasCommandPattern",   # [추론] 지휘 교체 패턴 - data property
        ],
        "inverse_properties": [
            "hist:participatesIn",      # 참여하다
            "hist:leadsTo",             # 인과관계 (양방향)
        ]
    },

    # 장소 (Place)
    "Place": {
        "properties": [
            "hist:locatedIn",           # 위치하다 (상위 지역)
            "hist:isLocationOf",        # ~의 장소이다 (사건)
            "hist:hasGeography",        # 지리적 특성
            "hist:controlledBy",        # 통제되다 (국가)

            # 인과관계 추론 결과 (Stage 2)
            "hist:strategicImportance", # [추론] 전략적 중요도 - data property

            # 패턴 추론 결과 (Stage 5)
            "hist:hasContestedStatus",  # [추론] 경합 지역 상태 - data property
        ],
        "inverse_properties": [
            "hist:occursAt",            # 발생하다
            "hist:bornIn",              # 태어나다
        ]
    },

    # 국가 (Nation)
    "Nation": {
        "properties": [
            "hist:engagesIn",           # 참여하다 (전쟁/사건)
            "hist:hasLeader",           # 지도자를 갖다
            "hist:controls",            # 통제하다 (장소)
            "hist:alliedWith",          # 동맹을 맺다
            "hist:atWarWith",           # 전쟁 중이다

            # 인과관계 추론 결과 (Stage 2)
            "hist:hasStatus",           # [추론] 국가 상태 (weakened 등) - data property

            # 패턴 추론 결과 (Stage 5)
            "hist:hasStrategyPattern",  # [추론] 전략 패턴 - data property
        ],
        "inverse_properties": [
            "hist:affiliatedWith",      # 소속되다
            "hist:involves",            # 포함되다
        ]
    },

    # 전투/해전 (Battle) - Event의 하위 클래스
    "Battle": {
        "properties": [
            "hist:occursAt",            # 발생 장소
            "hist:hasDate",             # 날짜
            "hist:hasCommander",        # 지휘관
            "hist:hasVictor",           # 승자
            "hist:hasDefeated",         # 패자
            "hist:casualtyCount",       # 사상자 수
            "hist:usedTactic",          # 사용된 전술
            "hist:partOf",              # 속한 전쟁
        ],
        "inverse_properties": [
            "hist:commands",            # 지휘하다
            "hist:participatesIn",      # 참여하다
        ]
    },

    # 연도 (Year)
    "Year": {
        "properties": [
            "hist:hasEvent",            # 사건을 갖다
            "hist:value",               # 연도 값 (리터럴)
        ],
        "inverse_properties": [
            "hist:hasYear",             # 연도를 갖다
            "hist:hasDate",             # 날짜를 갖다
        ]
    },

    # 인간관계 (Relationship) - 비하인드 스토리용
    "Relationship": {
        "properties": [
            "hist:between",             # 관계 당사자 (Person 2명)
            "hist:relationshipType",    # 관계 유형 (동료/적대/스승-제자/친구)
            "hist:inContext",           # 관련 사건
            "hist:hasDescription",      # 관계 설명
            "hist:startDate",           # 관계 시작 시점
            "hist:endDate",             # 관계 종료 시점
        ],
        "inverse_properties": [
            "hist:hasRelationship",     # 인간관계를 갖다
        ]
    },

    # 정책 (Policy) - Event의 하위 클래스
    "Policy": {
        "properties": [
            # 기본 정보
            "hist:hasDate",             # 날짜
            "hist:hasYear",             # 연도
            "hist:initiatedBy",         # 정책을 시작한 인물
            "hist:hasObjective",        # 정책 목표
            "hist:hasParticipant",      # 참여자

            # 인과관계
            "hist:leadsTo",             # ~로 이어지다
            "hist:causedBy",            # ~에 의해 발생하다
            "hist:hasImpact",           # 영향
            "hist:hasOutcome",          # 결과

            # 맥락
            "hist:partOf",              # ~의 일부
            "hist:hasContext",          # 시대적 맥락
            "hist:involves",            # 국가 포함

            # 시간 추론 결과 (Stage 4)
            "hist:occursBefore",        # [추론] ~보다 먼저
            "hist:occursAfter",         # [추론] ~보다 나중에
            "hist:simultaneousWith",    # [추론] 동일 시기
            "hist:belongsToPeriod",     # [추론] 역사적 시대

            # 인과관계 추론 결과 (Stage 2)
            "hist:indirectlyCausedBy",  # [추론] 간접 인과관계
        ],
        "inverse_properties": [
            "hist:participatesIn",      # 참여하다
        ]
    },

    # 제도 (Institution)
    "Institution": {
        "properties": [
            # 기본 정보
            "hist:establishedBy",       # 설립자
            "hist:hasPurpose",          # 목적
            "hist:relatedToPolicy",     # 관련 정책
            "hist:hasDate",             # 설립 날짜
            "hist:hasYear",             # 설립 연도

            # 맥락
            "hist:hasContext",          # 시대적 맥락
            "hist:partOf",              # ~의 일부
        ],
        "inverse_properties": [
            "hist:founded",             # 설립하다
            "hist:reformed",            # 개혁하다
        ]
    },

    # 문헌 (Document)
    "Document": {
        "properties": [
            # 기본 정보
            "hist:authoredBy",          # 저자
            "hist:hasYear",             # 저술 연도
            "hist:hasDate",             # 저술 날짜

            # 내용/분류
            "hist:hasSubject",          # 주제
            "hist:hasField",            # 분야 (실학, 성리학 등)

            # 영향
            "hist:influences",          # 영향을 주다
            "hist:leadsTo",             # ~로 이어지다

            # 맥락
            "hist:hasContext",          # 시대적 맥락
            "hist:partOf",              # ~의 일부 (총서 등)
        ],
        "inverse_properties": [
            "hist:authored",            # 저술하다
            "hist:compiled",            # 편찬하다
        ]
    }
}


# 엔티티 타입 → URI 프리픽스 매핑
ENTITY_URI_PREFIX: Dict[str, str] = {
    "Person": "hist:",
    "Event": "hist:",
    "Battle": "hist:",
    "Place": "hist:",
    "Nation": "hist:",
    "Policy": "hist:",
    "Institution": "hist:",
    "Document": "hist:",
    "Year": ""  # 연도는 리터럴
}


def get_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 속성 목록 반환

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle", "Year"

    Returns:
        해당 타입의 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    properties = schema.get("properties", [])
    return properties


def get_inverse_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 역방향 속성 목록 반환

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle", "Year"

    Returns:
        해당 타입의 역방향 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    inverse_properties = schema.get("inverse_properties", [])
    return inverse_properties


def get_all_properties() -> List[str]:
    """모든 속성 목록 반환 (중복 제거)"""
    all_props = set()
    for entity_type, schema in ONTOLOGY_SCHEMA.items():
        all_props.update(schema.get("properties", []))
        all_props.update(schema.get("inverse_properties", []))
    return sorted(list(all_props))


def get_schema_summary() -> Dict[str, any]:
    """
    스키마 요약 정보 반환 (MultiQueryGenerator에서 사용)

    Returns:
        {
            "classes": ["Person", "Event", "Place", ...],
            "properties_by_class": {
                "Person": ["hist:participatesIn", ...],
                "Event": ["hist:occursAt", ...]
            }
        }
    """
    return {
        "classes": list(ONTOLOGY_SCHEMA.keys()),
        "properties_by_class": {
            entity_type: schema.get("properties", [])
            for entity_type, schema in ONTOLOGY_SCHEMA.items()
        }
    }
