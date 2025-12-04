"""
TTL 프로퍼티를 의미 그룹으로 정리 (LLM 기반)

프로퍼티를 의미론적 그룹으로 분류하여 카테고리화

핵심 원칙:
1. LLM을 사용하여 프로퍼티의 의미를 분석하고 적절한 그룹에 분류
2. 단순 키워드 매칭이 아닌 의미론적 분류
3. 배치 처리로 API 호출 최소화 (20개씩)
"""

import os
import sys
import re
import json
from collections import defaultdict

# 프로젝트 루트 경로 찾기 (Python 모듈 경로 방식)
# 현재 파일: backend/ontology_langgraph_structure/ontology/scripts/extract_property_groups.py
# 프로젝트 루트: backend/ (상위 4단계)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_script_dir))))

# 환경변수 로드 (.env 파일 직접 읽기)
env_path = os.path.join(_project_root, ".env")
if os.path.exists(env_path):
    loaded_count = 0
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # 따옴표 제거 및 공백 제거
                value = value.strip().strip('"').strip("'")
                os.environ[key.strip()] = value
                loaded_count += 1
    # 디버깅: 환경변수 로드 확인 (필요시 주석 해제)
    # print(f"[DEBUG] .env 파일에서 {loaded_count}개 환경변수 로드됨")
else:
    # 디버깅: .env 파일 없음 경고 (필요시 주석 해제)
    # print(f"[DEBUG] WARNING: .env 파일을 찾을 수 없습니다: {env_path}")
    pass

# LangSmith 추적을 위해 langchain_openai 우선 사용, 없으면 requests 사용
try:
    from langchain_openai import ChatOpenAI
    USE_LANGCHAIN = True
except ImportError:
    USE_LANGCHAIN = False
    import requests

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
    "achievement": "출생",  # 통합: 업적 → 출생 그룹
    "award": "출생",  # 통합: 시상 → 출생 그룹
    "execut": "사망",  # 통합: 처형 → 사망 그룹

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
    "regulate": "정책",  # 통합: 규제 → 정책 그룹
    "tax": "세금",
    "address": "정책",
    "issue": "정책",
    "privilege": "정책",  # 통합: 권한 → 정책 그룹
    "quota": "정책",  # 통합: 할당 → 정책 그룹
    "permit": "정책",  # 통합: 허용 → 정책 그룹
    "prohibit": "정책",  # 통합: 금지 → 정책 그룹
    "restrict": "정책",  # 통합: 제한 → 정책 그룹
    "require": "정책",  # 통합: 필요 → 정책 그룹

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
    
    # 문서/기록
    "record": "문서",  # 통합: 기록 → 문서 그룹
    "document": "문서",
    "description": "문서",  # 통합: 설명 → 문서 그룹
    "definition": "문서",  # 통합: 정의 → 문서 그룹
    "summary": "문서",  # 통합: 개요 → 문서 그룹
    "list": "문서",  # 통합: 목록 → 문서 그룹
    "note": "문서",  # 통합: 비고 → 문서 그룹
    "problem": "문서",  # 통합: 문제 → 문서 그룹

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
    "involve": "참여",  # 통합: 관여 → 참여 그룹
    "attend": "참여",  # 통합: 참석 → 참여 그룹
    "join": "가입",
    "support": "지지",
    "ally": "동맹",
    "cooperat": "협력",
    "conflict": "갈등",
    "origin": "연결관계",  # 통합: 연관관계 → 연결관계 그룹
    "target": "연결관계",  # 통합: 대상 → 연결관계 그룹
    "for": "연결관계",  # 통합: 대상 → 연결관계 그룹

    # 연결관계 (우선순위 그룹에서 못 잡힌 것들)
    "related": "연결관계",
    "connect": "연결관계",
    "link": "연결관계",
    "associat": "연결관계",

    # 이동/변화
    "move": "위치",  # 통합: 이동 → 위치 그룹
    "transfer": "이전",
    "change": "변경",
    "convert": "전환",
    "restore": "복원",
    "replace": "교체",
    "inspect": "조사",
    "suspend": "정지",
    "promotion": "승진",
    "condition": "승진",  # 통합: 승진조건 → 승진 그룹

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
    "format": "속성",  # 통합: 형식 → 속성 그룹
    "variant": "속성",  # 통합: 변형 → 속성 그룹
    "range": "속성",  # 통합: 범위 → 속성 그룹
    "field": "속성",  # 통합: 분야 → 속성 그룹
    "topic": "속성",  # 통합: 주제 → 속성 그룹
    "focus": "속성",  # 통합: 주제 → 속성 그룹
    "decoration": "속성",  # 통합: 장식 → 속성 그룹
    "motive": "속성",  # 통합: 동기 → 속성 그룹
    "purpose": "속성",  # 통합: 목적 → 속성 그룹
    "restrict": "위치",  # 통합: 이동 → 위치 그룹 (restrictsMovementTo)

    # 시간 (범용)
    "year": "연도",
    "date": "날짜",
    "period": "시기",
    "era": "시대",
    "during": "기간중",
    "cycle": "시기",  # 통합: 주기 → 시기 그룹
    "every": "시기",  # 통합: 주기 → 시기 그룹
    
    # 추가 의미 그룹 (통합)
    "alternative": "연결관계",  # 통합: 대안 → 연결관계 그룹
    "appearance": "속성",  # 통합: 발현 → 속성 그룹
    "spread": "변경",  # 통합: 확산 → 변경 그룹
    "widespread": "변경",  # 통합: 확산 → 변경 그룹
    "temporary": "직위",  # 통합: 임시 → 직위 그룹
    "protocol": "시행",  # 통합: 절차 → 시행 그룹
    "observed": "시행",  # 통합: 절차 → 시행 그룹
    "same": "연결관계",  # 통합: 동일 → 연결관계 그룹
    "send": "연결관계",  # 통합: 발송 → 연결관계 그룹
    "sent": "연결관계",  # 통합: 발송 → 연결관계 그룹
    "receive": "연결관계",  # 통합: 수신 → 연결관계 그룹
    "subject": "학습",  
    "subtype": "상속",  
    "debate": "연결관계",  # 통합: 논쟁 → 연결관계 그룹
    "person": "연결관계",  # 통합: 대상 → 연결관계 그룹
    "movement": "위치",  # 통합: 이동 → 위치 그룹
}


def get_group_with_llm(property_batch: list) -> dict:
    """
    LLM을 사용하여 프로퍼티 배치를 의미론적으로 분류
    
    LangSmith 추적을 위해 ChatOpenAI 사용 (requests 직접 호출 대신)

    Args:
        property_batch: 프로퍼티 이름 리스트 (최대 20개)

    Returns:
        {property_name: group_name} 딕셔너리
    """
    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("  WARNING: OPENAI_API_KEY 없음, 키워드 기반으로 대체")
        return {prop: get_group_fallback(prop) for prop in property_batch}
    
    # LangSmith 추적을 위해 ChatOpenAI 사용
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("  WARNING: langchain_openai 없음, requests로 대체")
        return _get_group_with_requests(property_batch, api_key, model_name)
    
    # ChatOpenAI 사용 (LangSmith 자동 추적)
    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            timeout=120,  # 타임아웃 120초
            max_retries=2  # 재시도 2회
        )
        
        # 기존 그룹 목록 (룰 기반으로 생성된 그룹만 사용)
        existing_groups = list(set(PRIORITY_GROUPS.values()) | set(PROPERTY_GROUPS.values()))
        # "기타" 그룹 제거
        existing_groups = [g for g in existing_groups if g != "기타"]
        existing_groups_str = ", ".join(sorted(existing_groups))
        
        # 프로퍼티 리스트 문자열
        properties_str = "\n".join([f"{i+1}. {prop}" for i, prop in enumerate(property_batch)])
        
        prompt = f"""당신은 온톨로지 프로퍼티를 의미론적으로 분류하는 전문가입니다.

## 작업
아래 프로퍼티들을 조선시대 역사 온톨로지의 의미 그룹으로 분류하세요.
**중요: 반드시 아래 제공된 그룹 목록 중에서만 선택하세요. 새 그룹을 만들지 마세요.**

## 프로퍼티 목록
{properties_str}

## 사용 가능한 그룹 목록 (반드시 이 중에서만 선택)
{existing_groups_str}

## 분류 기준
1. 프로퍼티의 **의미**를 파악하여 가장 적합한 그룹 선택
2. **반드시 위 목록에 있는 그룹만 사용** - 새 그룹 생성 금지
3. 가장 유사한 의미의 그룹을 선택
   - 예: hasCause → "인과관계"
   - 예: hasWeight → "속성"
   - 예: hasBirthYear → "출생"
   - 예: hasDescription → "문서"
4. 정확히 매칭되지 않으면 가장 유사한 그룹 선택 (예: "속성", "연결관계" 등)

## 출력 형식 (JSON만)
{{
  "propertyName1": "그룹명",
  "propertyName2": "그룹명",
  ...
}}

예시:
{{
  "hasCause": "인과관계",
  "leadsTo": "인과관계",
  "hasWeight": "속성",
  "builtBy": "건설",
  "participatesIn": "참여",
  "manages": "관리",
  "restricts": "제한"
}}"""
        
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        result = json.loads(content)
        
        # 검증: 모든 프로퍼티가 결과에 있고, 유효한 그룹인지 확인
        valid_groups = set(existing_groups)
        for prop in property_batch:
            if prop not in result:
                # 기본값: 키워드 기반으로 대체
                result[prop] = get_group_fallback(prop)
            elif result[prop] not in valid_groups:
                # 유효하지 않은 그룹이면 키워드 기반으로 대체
                result[prop] = get_group_fallback(prop)
        
        return result
        
    except Exception as e:
        print(f"  WARNING: ChatOpenAI 분류 실패 ({str(e)[:100]}), requests로 대체")
        return _get_group_with_requests(property_batch, api_key, model_name)


def _get_group_with_requests(property_batch: list, api_key: str, model_name: str) -> dict:
    """
    requests를 사용한 OpenAI API 직접 호출 (LangSmith 추적 안됨, fallback용)
    """
    # 기존 그룹 목록 (룰 기반으로 생성된 그룹만 사용)
    existing_groups = list(set(PRIORITY_GROUPS.values()) | set(PROPERTY_GROUPS.values()))
    # "기타" 그룹 제거
    existing_groups = [g for g in existing_groups if g != "기타"]
    existing_groups_str = ", ".join(sorted(existing_groups))

    # 프로퍼티 리스트 문자열
    properties_str = "\n".join([f"{i+1}. {prop}" for i, prop in enumerate(property_batch)])

    prompt = f"""당신은 온톨로지 프로퍼티를 의미론적으로 분류하는 전문가입니다.

## 작업
아래 프로퍼티들을 조선시대 역사 온톨로지의 의미 그룹으로 분류하세요.
**중요: 반드시 아래 제공된 그룹 목록 중에서만 선택하세요. 새 그룹을 만들지 마세요.**

## 프로퍼티 목록
{properties_str}

## 사용 가능한 그룹 목록 (반드시 이 중에서만 선택)
{existing_groups_str}

## 분류 기준
1. 프로퍼티의 **의미**를 파악하여 가장 적합한 그룹 선택
2. **반드시 위 목록에 있는 그룹만 사용** - 새 그룹 생성 금지
3. 가장 유사한 의미의 그룹을 선택
   - 예: hasCause → "인과관계"
   - 예: hasWeight → "속성"
   - 예: hasBirthYear → "출생"
   - 예: hasDescription → "문서"
4. 정확히 매칭되지 않으면 가장 유사한 그룹 선택 (예: "속성", "연결관계" 등)

## 출력 형식 (JSON만)
{{
  "propertyName1": "그룹명",
  "propertyName2": "그룹명",
  ...
}}

예시:
{{
  "hasCause": "인과관계",
  "leadsTo": "인과관계",
  "hasWeight": "속성",
  "builtBy": "건설",
  "participatesIn": "참여",
  "manages": "관리",
  "restricts": "제한"
}}
"""

    try:
        # OpenAI API 직접 호출
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        # 타임아웃 설정: (연결 타임아웃, 읽기 타임아웃)
        # 연결: 10초, 읽기: 120초 (LLM 응답이 오래 걸릴 수 있음)
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(10, 120)  # (connect_timeout, read_timeout)
        )

        if response.status_code != 200:
            raise Exception(f"API 호출 실패: {response.status_code} - {response.text}")

        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"].strip()

        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        # 검증: 모든 프로퍼티가 결과에 있고, 유효한 그룹인지 확인
        valid_groups = set(existing_groups)
        for prop in property_batch:
            if prop not in result:
                # 기본값: 키워드 기반으로 대체
                result[prop] = get_group_fallback(prop)
            elif result[prop] not in valid_groups:
                # 유효하지 않은 그룹이면 키워드 기반으로 대체
                result[prop] = get_group_fallback(prop)

        return result

    except Exception as e:
        print(f"  WARNING: LLM 분류 실패 ({e}), 키워드 기반으로 대체")
        return {prop: get_group_fallback(prop) for prop in property_batch}


def get_group_fallback(property_name: str) -> str:
    """
    키워드 기반 분류 (기본 방법)
    
    우선순위:
    1. PRIORITY_GROUPS: 정확한 키워드 매칭
    2. PROPERTY_GROUPS: 부분 키워드 매칭
    3. 기타: 매칭 실패
    """
    prop_lower = property_name.lower()
    
    # 1. 우선순위 그룹 먼저 체크 (정확한 키워드)
    for keyword, group in PRIORITY_GROUPS.items():
        if keyword.lower() in prop_lower:
            return group

    # 2. 일반 그룹 체크 (부분 키워드)
    for prefix, group in PROPERTY_GROUPS.items():
        if prefix in prop_lower:
            return group
    
    # 3. 추가 패턴 매칭 (has로 시작하는 속성들)
    if prop_lower.startswith("has"):
        # has + 명사 패턴 분석
        if any(kw in prop_lower for kw in ["cause", "effect", "result", "consequence"]):
            return "인과관계"
        elif any(kw in prop_lower for kw in ["birth", "death"]):
            return "출생" if "birth" in prop_lower else "사망"
        elif any(kw in prop_lower for kw in ["year", "date", "period", "time", "when"]):
            return "연도"
        elif any(kw in prop_lower for kw in ["achievement", "award"]):
            return "출생"  # 통합: 업적, 시상, 칭호 → 출생 그룹
        elif any(kw in prop_lower for kw in ["privilege", "quota", "permit", "prohibit", "restrict", "require"]):
            return "정책"  # 통합: 정책 관련 → 정책 그룹
        elif any(kw in prop_lower for kw in ["description", "definition", "summary", "list", "note", "problem", "record"]):
            return "문서"  # 통합: 문서/기록 관련 → 문서 그룹
        elif any(kw in prop_lower for kw in ["format", "variant", "range", "field", "focus", "topic", "decoration", "motive", "purpose"]):
            return "속성"  # 통합: 속성/특성 관련 → 속성 그룹
        elif any(kw in prop_lower for kw in ["rank"]):
            return "품계"
        elif any(kw in prop_lower for kw in ["title"]):
            return "작위"
        elif any(kw in prop_lower for kw in ["weight", "dimension", "size", "color", "count", "number"]):
            return "속성"
        else:
            return "속성"  # has로 시작하면 기본적으로 속성
    
    # 4. 추가 패턴 매칭 (통합된 그룹 반환)
    if "executed" in prop_lower or "execute" in prop_lower:
        return "사망"  # 통합: 처형 → 사망 그룹
    if "award" in prop_lower:
        return "출생"  # 통합: 시상 → 출생 그룹
    if "address" in prop_lower and "issue" in prop_lower:
        return "정책"
    if "prohibit" in prop_lower or "permit" in prop_lower or "restrict" in prop_lower or "require" in prop_lower:
        return "정책"  # 통합: 정책 관련 → 정책 그룹
    if "restrict" in prop_lower and "movement" in prop_lower:
        return "위치"  # 통합: 이동 → 위치 그룹
    if "record" in prop_lower or "document" in prop_lower or "list" in prop_lower or "note" in prop_lower or "problem" in prop_lower:
        return "문서"  # 통합: 문서/기록 관련 → 문서 그룹
    if "attend" in prop_lower or "involve" in prop_lower:
        return "참여"  # 통합: 참석, 관여 → 참여 그룹
    if "for" in prop_lower and "person" in prop_lower or "origin" in prop_lower and "from" in prop_lower:
        return "연결관계"  # 통합: 대상, 연관관계 → 연결관계 그룹
    if "occur" in prop_lower and "every" in prop_lower or "cycle" in prop_lower:
        return "시기"  # 통합: 주기 → 시기 그룹
    if "inspect" in prop_lower:
        return "조사"
    if "suspend" in prop_lower:
        return "정지"
    if "promote" in prop_lower and "condition" in prop_lower:
        return "승진"  # 통합: 승진조건 → 승진 그룹
    if "promote" in prop_lower:
        return "승진"
    if "punish" in prop_lower:
        return "처벌"
    if "reform" in prop_lower:
        return "개혁"
    if "restore" in prop_lower:
        return "복원"
    if "replace" in prop_lower or "replacement" in prop_lower:
        return "교체"
    if "regular" in prop_lower and "into" in prop_lower:
        return "전환"
    if "alternative" in prop_lower or "same" in prop_lower and "as" in prop_lower or "send" in prop_lower or "debate" in prop_lower:
        return "연결관계"  # 통합: 대안, 동일, 발송, 수신, 논쟁 → 연결관계 그룹
    if "appearance" in prop_lower or "appear" in prop_lower:
        return "속성"  # 통합: 발현 → 속성 그룹
    if "widespread" in prop_lower or "spread" in prop_lower:
        return "변경"  # 통합: 확산 → 변경 그룹
    if "temporary" in prop_lower:
        return "직위"  # 통합: 임시 → 직위 그룹
    if "protocol" in prop_lower or "observed" in prop_lower:
        return "시행"  # 통합: 절차 → 시행 그룹
    if "subtype" in prop_lower:
        return "상속"
    
    # 5. 기타 패턴
    if "topic" in prop_lower or "subject" in prop_lower:
        return "포함"
    if "example" in prop_lower or "instance" in prop_lower:
        return "속성"
    if "classify" in prop_lower or "category" in prop_lower:
        return "속성"

    # 매칭 실패 시 기본값: "속성" (가장 범용적인 그룹)
    return "속성"


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


def group_properties(properties: list, use_llm: bool = False) -> dict:
    """
    프로퍼티를 그룹별로 분류
    
    그룹은 항상 룰 기반으로 생성되며, LLM은 기존 그룹에 프로퍼티를 매칭하는 역할만 수행
    
    Args:
        properties: 프로퍼티 리스트
        use_llm: LLM 사용 여부 (기본값: False, 키워드 기반만 사용)
                 True일 경우, 룰 기반 그룹에 LLM으로 프로퍼티 매칭
    
    Returns:
        {group_name: [property1, property2, ...]} 딕셔너리
    """
    # 먼저 룰 기반으로 모든 그룹 생성 (그룹 구조는 룰 기반으로 고정)
    groups = defaultdict(list)
    
    # 룰 기반으로 모든 프로퍼티를 분류하여 그룹 구조 생성
    print(f"  총 {len(properties)}개 프로퍼티를 룰 기반으로 그룹 생성 중...")
    for prop in properties:
        group = get_group_fallback(prop)
        groups[group].append(prop)
    
    # LLM을 사용하는 경우, 기존 그룹에 프로퍼티를 재매칭
    if use_llm:
        print(f"  LLM으로 프로퍼티를 기존 그룹에 재매칭 중...")
        batch_size = 20
        
        # 모든 프로퍼티를 LLM으로 재분류
        property_to_group_llm = {}
        for i in range(0, len(properties), batch_size):
            batch = properties[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(properties) + batch_size - 1) // batch_size

            print(f"    배치 {batch_num}/{total_batches} 처리 중... ({len(batch)}개)")

            # LLM으로 배치 분류 (기존 그룹에만 매칭)
            batch_result = get_group_with_llm(batch)
            property_to_group_llm.update(batch_result)
        
        # LLM 결과로 그룹 재구성
        groups = defaultdict(list)
        for prop in properties:
            group = property_to_group_llm.get(prop, get_group_fallback(prop))
            groups[group].append(prop)

    return dict(groups)


def create_property_mapping(ttl_path: str, output_path: str):
    """프로퍼티 매핑 파일 생성"""

    print(f"[1/3] TTL 파일 분석")
    print(f"  입력 파일: {ttl_path}")
    properties = extract_all_properties(ttl_path)
    print(f"  발견된 프로퍼티: {len(properties)}개")

    # LLM 사용 여부 결정 (환경변수 또는 기본값: false - 기본 그룹만 사용)
    use_llm = os.getenv("USE_LLM_FOR_PROPERTY_GROUPS", "false").lower() == "true"
    
    if use_llm:
        print(f"[2/3] 프로퍼티 그룹 분류 (LLM 기반)")
    else:
        print(f"[2/3] 프로퍼티 그룹 분류 (키워드 기반 - 기본 그룹만 사용)")
    
    groups = group_properties(properties, use_llm=use_llm)

    # 그룹별 통계
    print(f"  그룹별 분류 결과:")
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))

    for group_name, props in sorted_groups:
        print(f"    {group_name}: {len(props)}개")
        if len(props) <= 5:
            print(f"      → {props}")
        else:
            print(f"      → {props[:3]}... 외 {len(props)-3}개")

    # 결과 저장
    print(f"[3/3] 결과 저장")
    result = {
        "total_properties": len(properties),
        "total_groups": len(groups),
        "groups": {k: v for k, v in sorted_groups},
        "group_definitions": PROPERTY_GROUPS
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  출력 파일: {output_path}")
    print(f"  총 프로퍼티: {len(properties)}개")
    print(f"  총 그룹: {len(groups)}개")

    return result


if __name__ == "__main__":
    # Python 모듈 경로 방식으로 경로 찾기
    # 현재 파일: backend/ontology_langgraph_structure/ontology/scripts/extract_property_groups.py
    # scripts 디렉토리: backend/ontology_langgraph_structure/ontology/scripts/
    # ontology 디렉토리: backend/ontology_langgraph_structure/ontology/ (상위 1단계)
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    ontology_dir = os.path.dirname(_script_dir)  # scripts의 상위 = ontology
    
    ttl_path = os.path.join(ontology_dir, "instances", "korean_history_normalized.ttl")
    output_path = os.path.join(ontology_dir, "instances", "property_groups.json")

    print("=" * 60)
    print("프로퍼티 그룹 생성")
    print("=" * 60)
    print()

    if os.path.exists(ttl_path):
        create_property_mapping(ttl_path, output_path)
    else:
        print(f"ERROR: TTL 파일을 찾을 수 없습니다: {ttl_path}")

    print()
    print("=" * 60)
    print("완료")
    print("=" * 60)
