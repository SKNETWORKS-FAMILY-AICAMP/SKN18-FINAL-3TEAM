"""
TTL 프로퍼티를 의미 그룹으로 정리

4,000개 이상의 프로퍼티를 50~100개 카테고리로 축소

핵심 원칙:
1. 인과관계, 시간순서, 관계 프로퍼티는 별도 그룹으로 우선 분류
2. 구체적인 키워드가 더 우선순위 높음 (hasCause → 인과관계, has → 속성)
3. 범용 그룹(속성, 기타)은 최후 매칭
"""

import os
import re
from collections import defaultdict
from pathlib import Path

# ========================================
# 우선순위 높은 프로퍼티 매핑 (먼저 매칭)
# 인과관계, 시간순서, 관계 등 중요한 프로퍼티
# ========================================
PRIORITY_GROUPS = {
    # ★ 인과관계 (매우 중요!)
    "leadsTo": "인과관계",
    "ledTo": "인과관계",
    "causedBy": "인과관계",
    "hasCause": "인과관계",
    "hasEffect": "인과관계",
    "hasResult": "인과관계",
    "resultedIn": "인과관계",
    "triggeredBy": "인과관계",
    "consequence": "인과관계",
    "abolitionLedTo": "인과관계",
    "becameIneffective": "인과관계",
    
    # ★ 시간순서 (중요!)
    "occursBefore": "시간순서",
    "occursAfter": "시간순서",
    "followedBy": "시간순서",
    "precededBy": "시간순서",
    "advancedAfter": "시간순서",
    "performsBefore": "시간순서",
    "succeededBy": "시간순서",
    "priorTo": "시간순서",
    
    # ★ 관계/연결 (중요!)
    "isRelatedTo": "연결관계",
    "relatedTo": "연결관계",
    "connectedTo": "연결관계",
    "linkedTo": "연결관계",
    "associatedWith": "연결관계",
    "hasRelationshipWith": "연결관계",
    "relatedConcept": "연결관계",
    "relatedPlace": "연결관계",
    "relatedPeriod": "연결관계",
}

# ========================================
# 일반 프로퍼티 → 의미 그룹 매핑
# ========================================
PROPERTY_GROUPS = {
    # 생애/인물
    "birth": "출생",
    "born": "출생",
    "die": "사망",
    "death": "사망",
    "kill": "살해",
    "murder": "살해",
    "marry": "혼인",
    "marriage": "혼인",
    "spouse": "배우자",
    "parent": "부모",
    "child": "자녀",
    "son": "자녀",
    "daughter": "자녀",
    "sibling": "형제",
    "family": "가족",
    "descend": "후손",
    "ancestor": "조상",
    "adopt": "입양",
    
    # 직위/관직
    "appoint": "임명",
    "promote": "승진",
    "demote": "강등",
    "dismiss": "해임",
    "resign": "사임",
    "retire": "은퇴",
    "rank": "품계",
    "position": "직위",
    "title": "작위",
    "office": "관직",
    "role": "역할",
    
    # 건설/창건
    "build": "건설",
    "built": "건설",
    "construct": "건설",
    "found": "설립",
    "establish": "설립",
    "creat": "창제",
    "make": "제작",
    "design": "설계",
    
    # 폐지/파괴
    "abolish": "폐지",
    "destroy": "파괴",
    "demolish": "철거",
    "dissolve": "해산",
    
    # 정치/권력
    "reign": "재위",
    "rule": "통치",
    "govern": "통치",
    "succeed": "계승",
    "inherit": "상속",
    "throne": "왕위",
    "crown": "즉위",
    "abdicate": "양위",
    
    # 갈등/처벌
    "accus": "고발",
    "punish": "처벌",
    "exile": "유배",
    "execut": "처형",
    "imprison": "투옥",
    "arrest": "체포",
    "trial": "재판",
    "convict": "유죄",
    "acquit": "무죄",
    
    # 전쟁/군사
    "attack": "공격",
    "defend": "방어",
    "invade": "침입",
    "battle": "전투",
    "war": "전쟁",
    "victory": "승리",
    "defeat": "패배",
    "command": "지휘",
    "military": "군사",
    "troop": "군대",
    
    # 반란/저항
    "rebel": "반란",
    "revolt": "봉기",
    "uprising": "봉기",
    "resist": "저항",
    "oppos": "반대",
    "suppress": "진압",
    
    # 정책/제도
    "implement": "시행",
    "enforce": "시행",
    "policy": "정책",
    "reform": "개혁",
    "law": "법률",
    "decree": "칙령",
    "regulate": "규제",
    "tax": "세금",
    
    # 외교
    "diploma": "외교",
    "treaty": "조약",
    "alliance": "동맹",
    "tribute": "조공",
    "embassy": "사신",
    
    # 문화/학문
    "wrote": "저술",
    "write": "저술",
    "author": "저술",
    "publish": "출판",
    "study": "학습",
    "teach": "교육",
    "scholar": "학자",
    "confuc": "유학",
    "buddhis": "불교",
    
    # 인과/결과 (우선순위 그룹에서 못 잡힌 것들)
    "cause": "인과관계",
    "result": "인과관계",
    "effect": "인과관계",
    "lead": "인과관계",
    "trigger": "인과관계",
    
    # 시간순서 (우선순위 그룹에서 못 잡힌 것들)
    "before": "시간순서",
    "after": "시간순서",
    "prior": "시간순서",
    "follow": "시간순서",
    
    # 참여/관계
    "particip": "참여",
    "involve": "관여",
    "attend": "참석",
    "join": "가입",
    "support": "지지",
    "ally": "동맹",
    "cooperat": "협력",
    "conflict": "갈등",
    
    # 연결관계 (우선순위 그룹에서 못 잡힌 것들)
    "related": "연결관계",
    "connect": "연결관계",
    "link": "연결관계",
    "associat": "연결관계",
    
    # 이동/변화
    "move": "이동",
    "transfer": "이전",
    "change": "변경",
    "convert": "전환",
    "restore": "복원",
    "replace": "교체",
    
    # ========================================
    # 낮은 우선순위 (범용 그룹) - 마지막에 매칭
    # ========================================
    "has": "속성",      # hasCause, hasEffect는 우선순위 그룹에서 먼저 잡힘
    "contain": "포함",
    "include": "포함",
    "belong": "소속",
    "member": "구성원",
    "part": "부분",
    "locat": "위치",
    "place": "장소",
    
    # 시간 (범용)
    "year": "연도",
    "date": "날짜",
    "period": "시기",
    "era": "시대",
    "during": "기간중",
}


def get_group(property_name: str) -> str:
    """
    프로퍼티명에서 의미 그룹 추출
    
    우선순위:
    1. PRIORITY_GROUPS: 정확히 일치하는 중요 프로퍼티 (hasCause, leadsTo 등)
    2. PROPERTY_GROUPS: 부분 일치하는 일반 프로퍼티 (cause, lead 등)
    3. 기타: 매칭 안 되는 프로퍼티
    """
    
    # 1. 우선순위 그룹 먼저 체크 (정확 매칭 또는 포함)
    for keyword, group in PRIORITY_GROUPS.items():
        if keyword.lower() in property_name.lower():
            return group
    
    # 2. 일반 그룹 체크 (부분 매칭)
    prop_lower = property_name.lower()
    for prefix, group in PROPERTY_GROUPS.items():
        if prefix in prop_lower:
            return group
    
    return "기타"


def extract_all_properties(ttl_path: str) -> list:
    """TTL 파일에서 모든 프로퍼티 추출"""
    properties = set()
    
    with open(ttl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # hist:propertyName 패턴 추출
    pattern = r'hist:([a-z][a-zA-Z]*)'
    matches = re.findall(pattern, content)
    properties.update(matches)
    
    return sorted(list(properties))


def group_properties(properties: list) -> dict:
    """프로퍼티를 그룹별로 분류"""
    groups = defaultdict(list)
    
    for prop in properties:
        group = get_group(prop)
        groups[group].append(prop)
    
    return dict(groups)


def create_property_mapping(ttl_path: str, output_path: str):
    """프로퍼티 매핑 파일 생성"""
    
    print(f"📂 TTL 파일 분석: {ttl_path}")
    properties = extract_all_properties(ttl_path)
    print(f"   총 {len(properties)}개 프로퍼티 발견")
    
    groups = group_properties(properties)
    
    # 그룹별 통계
    print(f"\n📊 그룹별 분류 결과:")
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
    
    for group_name, props in sorted_groups:
        print(f"   {group_name}: {len(props)}개")
        if len(props) <= 5:
            print(f"      → {props}")
        else:
            print(f"      → {props[:3]}... 외 {len(props)-3}개")
    
    # 결과 저장
    import json
    result = {
        "total_properties": len(properties),
        "total_groups": len(groups),
        "groups": {k: v for k, v in sorted_groups},
        "group_definitions": PROPERTY_GROUPS
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 저장 완료: {output_path}")
    
    return result


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    ttl_path = base_dir / "instances" / "korean_history_normalized.ttl"
    output_path = base_dir / "instances" / "property_groups.json"
    
    if ttl_path.exists():
        create_property_mapping(str(ttl_path), str(output_path))
    else:
        print(f"❌ TTL 파일을 찾을 수 없습니다: {ttl_path}")

