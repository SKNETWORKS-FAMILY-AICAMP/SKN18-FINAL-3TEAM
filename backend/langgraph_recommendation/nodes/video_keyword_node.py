"""
Video Keyword Extraction Node

video_title에서 키워드를 추출하는 노드:
1. Kiwi 형태소 분석으로 명사 추출
2. TTL 데이터와 매칭
3. 매칭된 키워드를 콤마 구분 문자열로 반환
"""

import os
import re
from typing import List
from backend.langgraph_recommendation.state import RecommendationState

# Kiwi 형태소 분석기
try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    USE_KIWI = True
except ImportError:
    _kiwi = None
    USE_KIWI = False
    print("⚠️ kiwipiepy를 사용할 수 없습니다. 간단한 정규식 기반 키워드 추출을 사용합니다.")

# TTL 캐시
_ttl_cache = None
_ttl_cache_mtime = None


def load_ttl_entities() -> dict:
    """
    TTL 파일에서 모든 엔티티 label 로드 (캐싱)
    fuseki의 entity_expander_node.py 로직 재사용

    Returns:
        {
            "label_to_uri": {"경복궁": "hist:Place_경복궁", ...},
            "uri_to_type": {"hist:Place_경복궁": "Place", ...}
        }
    """
    global _ttl_cache, _ttl_cache_mtime

    # TTL 경로 (fuseki와 동일)
    from backend.langgraph_fuseki.config import TTL_PATH

    # 캐시 유효성 검사
    if os.path.exists(TTL_PATH):
        current_mtime = os.path.getmtime(TTL_PATH)
        if _ttl_cache is not None and _ttl_cache_mtime == current_mtime:
            return _ttl_cache

    label_to_uri = {}
    uri_to_type = {}

    if not os.path.exists(TTL_PATH):
        print(f"⚠️ TTL 파일이 없습니다: {TTL_PATH}")
        return {"label_to_uri": {}, "uri_to_type": {}}

    try:
        with open(TTL_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # 타입 추출: hist:Entity_Name rdf:type hist:Type .
        type_pattern = r'(hist:\w+_[^\s]+)\s+rdf:type\s+hist:(\w+)\s*\.'
        for match in re.finditer(type_pattern, content):
            uri = match.group(1)
            entity_type = match.group(2)
            uri_to_type[uri] = entity_type

        # 라벨 추출: hist:Entity_Name rdfs:label "Label" .
        label_pattern = r'(hist:\w+_[^\s]+)\s+rdfs:label\s+"([^"]+)"\s*\.'
        for match in re.finditer(label_pattern, content):
            uri = match.group(1)
            label = match.group(2)
            label_to_uri[label] = uri

            # 라벨 변형도 추가 (공백 제거)
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri

            # 괄호 앞 부분만
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri

        print(f"✓ TTL 엔티티 로드 완료: {len(label_to_uri)}개 라벨")

    except Exception as e:
        print(f"⚠️ TTL 파일 로드 실패: {e}")

    # 캐시 저장
    result = {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}
    _ttl_cache = result
    _ttl_cache_mtime = os.path.getmtime(TTL_PATH) if os.path.exists(TTL_PATH) else None

    return result


def extract_keywords_with_kiwi(title: str) -> List[str]:
    """
    Kiwi 형태소 분석으로 키워드 추출
    fuseki의 classify_node.py 로직 재사용
    """
    if not USE_KIWI or _kiwi is None:
        # fallback: 간단한 한글 단어 추출
        words = re.findall(r'[가-힣]{2,}', title)
        return [w for w in words if w not in {'무엇', '누구', '어디', '언제', '어떤', '왜', '조선', '조선시대'}]

    try:
        tokens = _kiwi.tokenize(title)
        keywords = []

        for token in tokens:
            # 명사(NNG, NNP)만 추출
            if token.tag in ('NNG', 'NNP') and len(token.form) >= 2:
                # 불용어 제거
                if token.form not in {'무엇', '누구', '어디', '언제', '어떤', '왜', '조선', '조선시대'}:
                    keywords.append(token.form)

        return keywords
    except Exception as e:
        print(f"⚠️ Kiwi 키워드 추출 실패: {e}")
        return []


def video_keyword_node(state: RecommendationState) -> RecommendationState:
    """
    Stage 1: user_query + video_title에서 키워드 추출

    작업:
    1. Kiwi 형태소 분석으로 쿼리와 제목에서 명사 추출
    2. TTL 데이터와 매칭
    3. 매칭된 키워드를 콤마 구분 문자열로 반환

    에러 처리:
    - 매칭된 키워드가 없으면 Kiwi가 추출한 키워드를 그대로 사용
    - 모두 실패하면 빈 문자열 반환
    """
    print(f"\n{'='*70}")
    print(f"[Stage 1] Video Keyword Extraction (Query + Title)")
    print(f"{'='*70}")

    user_query = state.get("user_query", "")
    video_title = state.get("video_title", "")
    print(f"  사용자 쿼리: '{user_query}'")
    print(f"  영상 제목: '{video_title}'")

    if not video_title and not user_query:
        print(f"  ⚠️ video_title과 user_query가 모두 비어있습니다.")
        return {
            **state,
            "basic_keywords": [],
            "video_keywords": "",
            "errors": state.get("errors", []) + ["video_title과 user_query 모두 비어있음"],
            "executed_nodes": state.get("executed_nodes", []) + ["video_keyword_extraction"]
        }

    # 1. Kiwi 형태소 분석 (쿼리 + 제목)
    query_keywords = extract_keywords_with_kiwi(user_query) if user_query else []
    title_keywords = extract_keywords_with_kiwi(video_title) if video_title else []

    # 중복 제거 및 결합
    basic_keywords = list(dict.fromkeys(query_keywords + title_keywords))

    print(f"  Kiwi 추출 키워드 (쿼리): {query_keywords}")
    print(f"  Kiwi 추출 키워드 (제목): {title_keywords}")
    print(f"  통합 키워드: {basic_keywords} ({len(basic_keywords)}개)")

    if not basic_keywords:
        print(f"  ⚠️ Kiwi 키워드 추출 실패")
        return {
            **state,
            "basic_keywords": [],
            "video_keywords": "",
            "errors": state.get("errors", []) + ["Kiwi 키워드 추출 실패"],
            "executed_nodes": state.get("executed_nodes", []) + ["video_keyword_extraction"]
        }

    # 2. TTL 매칭
    ttl_data = load_ttl_entities()
    matched_keywords = []

    for keyword in basic_keywords:
        # 정확한 라벨 매칭
        if keyword in ttl_data.get("label_to_uri", {}):
            matched_keywords.append(keyword)
            print(f"    ✓ TTL 매칭: {keyword}")

    # 3. 결과 생성
    if matched_keywords:
        # TTL에 매칭된 키워드가 있으면 사용
        video_keywords_str = ",".join(matched_keywords)
        print(f"  최종 video_keywords: {video_keywords_str}")
    else:
        # 매칭 실패 시 Kiwi 키워드 사용
        video_keywords_str = ",".join(basic_keywords)
        print(f"  ⚠️ TTL 매칭 실패, Kiwi 키워드 사용: {video_keywords_str}")

    return {
        **state,
        "basic_keywords": basic_keywords,
        "video_keywords": video_keywords_str,
        "executed_nodes": state.get("executed_nodes", []) + ["video_keyword_extraction"]
    }
