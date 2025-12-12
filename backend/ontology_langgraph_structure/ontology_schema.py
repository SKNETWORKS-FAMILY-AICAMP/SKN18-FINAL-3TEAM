"""
온톨로지 스키마 정의 (korean_history.owl 기반)

korean_history.owl에서 정의된 클래스와 프로퍼티를 기반으로 함
"""

from typing import Dict, List, Any

# =============================================================================
# 온톨로지 클래스 및 속성 매핑 (OWL 기반)
# =============================================================================
ONTOLOGY_SCHEMA: Dict[str, Dict[str, List[str]]] = {
    # 인물 (Person) - 106,122개 인스턴스
    "Person": {
        "object_properties": [
            # 참여/관계
            "hist:participatesIn",      # 사건에 참여하다
            "hist:affiliatedWith",      # 국가/당파에 소속되다
            "hist:servedUnder",         # 군주 아래에서 섬기다
            "hist:contemporaryWith",    # 동시대를 살다
            
            # 학문/교육
            "hist:authored",            # 문헌을 저술하다
            "hist:compiled",            # 문헌을 편찬하다
            "hist:studentOf",           # 제자이다
            "hist:teacherOf",           # 스승이다
            
            # 제도/설립
            "hist:founded",             # 기관을 설립하다
            "hist:reformed",            # 제도를 개혁하다
            
            # 전투/지휘
            "hist:commands",            # 전투를 지휘하다
        ],
        "data_properties": [
            "hist:hasBirthYear",        # 출생년도
            "hist:hasDeathYear",        # 사망년도
            "hist:hasReignStart",       # 재위 시작년도
            "hist:hasReignEnd",         # 재위 종료년도
            "hist:executedInYear",      # 처형년도
            "hist:hasRank",             # 직위/관직/품계
            "hist:hasAchievement",      # 업적
            "hist:hasField",            # 학문 분야
            "hist:hasMotive",           # 동기
            "hist:hasAlias",            # 별칭
            "hist:hasTitle",            # 작위/칭호
        ],
        "inverse_properties": [
            "hist:establishedBy",       # ~에 의해 설립되다
            "hist:initiatedBy",         # ~에 의해 시작되다
        ]
    },

    # 사건 (Event) - 63,947개 인스턴스
    "Event": {
        "object_properties": [
            # 참여/관계
            "hist:involvesPerson",      # 인물을 포함하다
            "hist:attendedBy",          # 인물이 참석하다
            
            # 인과관계
            "hist:leadsTo",             # 다른 사건으로 이어지다 (TransitiveProperty)
            "hist:ledTo",               # 다른 사건으로 이어지다 (과거형)
            "hist:causes",              # 원인이 되다
            "hist:derivedFrom",         # 유래하다
            
            # 장소
            "hist:occursAt",            # 장소에서 발생하다
            "hist:heldAt",              # 장소에서 개최되다
            
            # 부분/포함
            "hist:partOf",              # 상위 사건의 일부이다 (TransitiveProperty)
            "hist:hasPart",             # 하위 사건을 포함하다
            
            # 문서
            "hist:documentsEvent",      # 사건을 기록하다
        ],
        "data_properties": [
            "hist:hasYear",             # 연도
            "hist:hasStartYear",        # 시작년도
            "hist:hasEndYear",          # 종료년도
            "hist:hasMonth",            # 월
            "hist:occurredInYear",      # 발생년도
            "hist:period",              # 기간
            "hist:practicedDuring",     # 시행 기간
            "hist:hasPurpose",          # 목적
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:participatesIn",      # 참여하다
        ]
    },

    # 제도/기관 (Institution) - 60,067개 인스턴스
    "Institution": {
        "object_properties": [
            "hist:establishedBy",       # 인물에 의해 설립되다
            "hist:commonInstitutions",  # 공통 기관
            "hist:registeredThrough",   # ~을 통해 등록되다
            "hist:includesPositions",   # 직위를 포함하다
            "hist:contains",            # 포함하다
        ],
        "data_properties": [
            "hist:hasYear",             # 설립 연도
            "hist:hasStartYear",        # 시작년도
            "hist:hasEndYear",          # 종료년도
            "hist:hasFunction",         # 기능/역할
            "hist:hasPurpose",          # 목적
            "hist:hasStaffCountFor",    # 인원 구성
            "hist:servantRoleName",     # 하인 역할명
            "hist:hasFocusTopics",      # 주요 주제
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:founded",             # 설립하다
            "hist:reformed",            # 개혁하다
        ]
    },

    # 문헌 (Document) - 9,098개 인스턴스
    "Document": {
        "object_properties": [
            "hist:documents",           # 기록하다
            "hist:documentsEvent",      # 사건을 기록하다
            "hist:records",             # 기록하다
            "hist:lists",               # 목록에 포함하다
            "hist:subjects",            # 주제/대상
            "hist:containsTopic",       # 주제를 포함하다
            "hist:storedAt",            # 보관 장소
            "hist:isStoredAt",          # 보관되다
        ],
        "data_properties": [
            "hist:hasYear",             # 저술 연도
            "hist:hasCreationYear",     # 제작년도
            "hist:hasCreationMonth",    # 제작월
            "hist:hasVolumes",          # 권수
            "hist:hasFormat",           # 형식
            "hist:hasDimensions",       # 크기
            "hist:hasDesignation",      # 지정 (보물, 국보 등)
            "hist:hasDesignations",     # 지정들
            "hist:hasDesignationYear",  # 지정년도
            "hist:hasCurrentLocation",  # 현재 소장 위치
            "hist:hasSignificance",     # 의의
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
            "hist:notes",               # 참고사항
            "hist:notedProblems",       # 기록된 문제점
        ],
        "inverse_properties": [
            "hist:authored",            # 저술하다
            "hist:compiled",            # 편찬하다
        ]
    },

    # 국가 (Nation) - 6,809개 인스턴스
    "Nation": {
        "object_properties": [
            "hist:wasMostlyAffiliatedWith",  # 주로 소속되었다
            "hist:restoredPowerTo",          # 권력을 회복시키다
        ],
        "data_properties": [
            "hist:hasYear",             # 연도
            "hist:hasStartYear",        # 건국년도
            "hist:hasEndYear",          # 멸망년도
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:affiliatedWith",      # 소속되다
        ]
    },

    # 장소 (Place) - 1,769개 인스턴스
    "Place": {
        "object_properties": [
            "hist:hasLocation",         # 위치를 갖다
            "hist:originatedIn",        # 유래하다
        ],
        "data_properties": [
            "hist:location",            # 위치
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:occursAt",            # 발생하다
            "hist:heldAt",              # 개최되다
            "hist:storedAt",            # 보관되다
        ]
    },

    # 전투 (Battle) - 1,446개 인스턴스, Event의 하위 클래스
    "Battle": {
        "parent_class": "Event",
        "object_properties": [
            "hist:occursAt",            # 발생 장소
            "hist:partOf",              # 속한 전쟁
        ],
        "data_properties": [
            "hist:hasYear",             # 연도
            "hist:hasMonth",            # 월
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:commands",            # 지휘하다
            "hist:participatesIn",      # 참여하다
        ]
    },

    # 정책 (Policy) - 1,028개 인스턴스, Event의 하위 클래스
    "Policy": {
        "parent_class": "Event",
        "object_properties": [
            "hist:initiatedBy",         # 인물에 의해 시작되다
            "hist:leadsTo",             # 다른 사건으로 이어지다
            "hist:causes",              # 원인이 되다
        ],
        "data_properties": [
            "hist:hasYear",             # 연도
            "hist:hasPurpose",          # 목적
            "hist:permitted",           # 허용된
            "hist:promotionCondition",  # 승진 조건
            "hist:hasQuota",            # 할당량
            "hist:practicedDuring",     # 시행 기간
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": [
            "hist:participatesIn",      # 참여하다
        ]
    },

    # 물품 (Object) - 8개 인스턴스
    "Object": {
        "object_properties": [
            "hist:usedBy",              # ~에 의해 사용되다
            "hist:usedIn",              # ~에서 사용되다
            "hist:pairedWith",          # 짝을 이루다 (SymmetricProperty)
            "hist:designatesWornPrisonerAs",  # 착용한 죄수 지칭
            "hist:prohibitedFor",       # ~에 대해 금지되다
        ],
        "data_properties": [
            "hist:hasWeight",           # 무게
            "hist:hasDimensions",       # 크기
            "hist:hasCategory",         # 분류
            "hist:category",            # 분류
            "hist:hasCharacteristics",  # 특징
            "hist:hasVariant",          # 변형
            "hist:typicalUsage",        # 일반적 용도
            "hist:usedSince",           # 사용 시작 시기
            "hist:examplesRegularizedLater",  # 후에 정규화된 예시
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": []
    },

    # 역할 (Role) - 4개 인스턴스
    "Role": {
        "object_properties": [],
        "data_properties": [
            "hist:hasFunction",         # 기능
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": []
    },

    # 사회계층 (SocialClass) - 4개 인스턴스
    "SocialClass": {
        "object_properties": [],
        "data_properties": [
            "hist:hasCharacteristics",  # 특징
            "hist:description",         # 설명
            "hist:hasDescription",      # 설명을 갖다
            "hist:hasSummary",          # 요약
        ],
        "inverse_properties": []
    },
}


# =============================================================================
# 엔티티 타입 → URI 프리픽스 매핑
# =============================================================================
ENTITY_URI_PREFIX: Dict[str, str] = {
    "Person": "hist:Person_",
    "Event": "hist:Event_",
    "Battle": "hist:Battle_",
    "Place": "hist:Place_",
    "Nation": "hist:Nation_",
    "Policy": "hist:Policy_",
    "Institution": "hist:Institution_",
    "Document": "hist:Document_",
    "Object": "hist:Object_",
    "Role": "hist:Role_",
    "SocialClass": "hist:SocialClass_",
}


# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 모든 속성 목록 반환 (object + data)

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle" 등

    Returns:
        해당 타입의 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    properties = []
    properties.extend(schema.get("object_properties", []))
    properties.extend(schema.get("data_properties", []))
    return properties


def get_object_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 객체 속성 목록 반환

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle" 등

    Returns:
        해당 타입의 객체 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    return schema.get("object_properties", [])


def get_data_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 데이터 속성 목록 반환

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle" 등

    Returns:
        해당 타입의 데이터 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    return schema.get("data_properties", [])


def get_inverse_properties_for_type(entity_type: str) -> List[str]:
    """
    엔티티 타입에 대한 역방향 속성 목록 반환

    Args:
        entity_type: "Person", "Event", "Place", "Nation", "Battle" 등

    Returns:
        해당 타입의 역방향 속성 목록
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    return schema.get("inverse_properties", [])


def get_all_properties() -> List[str]:
    """모든 속성 목록 반환 (중복 제거)"""
    all_props = set()
    for entity_type, schema in ONTOLOGY_SCHEMA.items():
        all_props.update(schema.get("object_properties", []))
        all_props.update(schema.get("data_properties", []))
        all_props.update(schema.get("inverse_properties", []))
    return sorted(list(all_props))


def get_all_classes() -> List[str]:
    """모든 클래스 목록 반환"""
    return list(ONTOLOGY_SCHEMA.keys())


def get_parent_class(entity_type: str) -> str:
    """
    엔티티 타입의 부모 클래스 반환 (없으면 None)
    
    Args:
        entity_type: "Battle", "Policy" 등
        
    Returns:
        부모 클래스 이름 (없으면 None)
    """
    schema = ONTOLOGY_SCHEMA.get(entity_type, {})
    return schema.get("parent_class")


def get_schema_summary() -> Dict[str, Any]:
    """
    스키마 요약 정보 반환 (entity_expander_node에서 사용)

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
        "classes": get_all_classes(),
        "properties_by_class": {
            entity_type: get_properties_for_type(entity_type)
            for entity_type in ONTOLOGY_SCHEMA.keys()
        }
    }
