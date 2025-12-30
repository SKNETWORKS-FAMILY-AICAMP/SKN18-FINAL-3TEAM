"""
Entity Expander Node

질문에서 핵심 엔티티 추출 및 TTL 데이터 매칭:
1. 형태소 분석기(kiwipiepy)로 명사 추출
2. 키워드 확장 (classify_node에서 처리된 확장된 키워드 사용)
3. TTL 정확 매칭 (확장된 키워드 + 원본 키워드 모두 사용)
4. pgvector 제목 임베딩 유사도 검색 (fallback)
5. LLM 엔티티 추출 (최종 fallback)
6. 엔티티 URI 반환

+ 추출된 엔티티 타입에 맞는 온톨로지 스키마 정보 제공

주의: Fuseki 검색은 제거되었으며, TTL 파일에서 직접 매칭합니다.
"""

import os
import sys
import re
import json
import time
import threading
import queue
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
from backend.langgraph_fuseki.utils.fuseki_client import execute_sparql_query

# 한국어 형태소 분석기 (조사/어미 자동 제거)
try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    USE_KIWI = True
    print("[INFO] kiwipiepy 형태소 분석기 로드 완료")
except ImportError:
    _kiwi = None
    USE_KIWI = False
    print("[WARN] kiwipiepy 미설치 - 규칙 기반 조사 제거 사용")

# config.py에서 환경변수 자동 로드
from backend.langgraph_fuseki.config import TTL_PATH, USE_PGVECTOR
from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.ontology_schema import get_schema_summary

# pgvector 제목 임베딩 서비스 import (선택적)
_title_vector_service = None

def get_title_vector_service():
    """제목 임베딩 pgvector 서비스 lazy loading (최적화된 버전)"""
    global _title_vector_service
    if _title_vector_service is None and USE_PGVECTOR:
        try:
            # 성능 최적화된 지연 로딩 서비스 시도
            config = get_performance_config()
            if config and config.lazy_load_vectors:
                from backend.langgraph_fuseki.utils.performance_optimizer import LazyVectorService
                _title_vector_service = LazyVectorService(config)
                print("  ├─ [INFO] 최적화된 벡터 서비스 초기화")
            else:
                # 기존 방식
                from backend.db_pipeline.postgres.services.title_vector_service import TitleVectorService
                _title_vector_service = TitleVectorService()
                print("  ├─ [INFO] 제목 임베딩 pgvector 서비스 초기화 완료")
        except ImportError:
            print("  ├─ [WARN] 제목 임베딩 pgvector 서비스 import 실패 - TTL 매칭만 사용")
        except Exception as e:
            print(f"  ├─ [WARN] 제목 임베딩 pgvector 초기화 실패: {e}")
    return _title_vector_service


# TTL 데이터 캐시 (매번 파일 읽지 않도록)
_ttl_cache = None
_ttl_cache_mtime = None


# 최적화된 TTL 로더 및 성능 설정
_optimized_ttl_loader = None
_performance_config = None

def get_performance_config():
    """성능 설정 가져오기"""
    global _performance_config
    if _performance_config is None:
        try:
            from backend.langgraph_fuseki.utils.performance_optimizer import PerformanceConfig
            _performance_config = PerformanceConfig(
                max_workers=4,
                sparql_batch_size=10,
                sparql_timeout=3,
                enable_ttl_cache=True,
                lazy_load_vectors=True
            )
            print("  ├─ [INFO] 성능 최적화 설정 로드 완료")
        except ImportError as e:
            print(f"  ├─ [WARN] 성능 최적화 모듈 import 실패: {e}")
            _performance_config = None
        except Exception as e:
            print(f"  ├─ [WARN] 성능 최적화 설정 실패: {e}")
            _performance_config = None
    return _performance_config


def load_ttl_entities() -> dict:
    """
    TTL 파일에서 모든 엔티티와 label 로드 (최적화된 버전)
    
    Returns:
        {
            "label_to_uri": {"심기원역모사건": "hist:Event_심기원역모사건", ...},
            "uri_to_type": {"hist:Event_심기원역모사건": "Event", ...}
        }
    """
    global _ttl_cache, _ttl_cache_mtime, _optimized_ttl_loader
    
    # 성능 최적화 모듈 사용 시도
    config = get_performance_config()
    if config and _optimized_ttl_loader is None:
        try:
            from backend.langgraph_fuseki.utils.performance_optimizer import OptimizedTTLLoader
            _optimized_ttl_loader = OptimizedTTLLoader(TTL_PATH, config)
            print("  │   ✓ 최적화된 TTL 로더 사용")
            return _optimized_ttl_loader.load_entities_parallel()
        except ImportError:
            print("  ├─ [INFO] 성능 최적화 모듈 없음, 기본 로더 사용")
    
    if _optimized_ttl_loader:
        return _optimized_ttl_loader.load_entities_parallel()
    
    # 기본 TTL 로더 (기존 코드)
    # 캐시 유효성 검사 (파일 수정 시간 비교)
    if os.path.exists(TTL_PATH):
        current_mtime = os.path.getmtime(TTL_PATH)
        if _ttl_cache is not None and _ttl_cache_mtime == current_mtime:
            return _ttl_cache  # 캐시 반환 (파일 I/O 생략)
    
    label_to_uri = {}
    uri_to_type = {}
    
    if not os.path.exists(TTL_PATH):
        print(f"  ├─ [WARN] TTL 파일이 없습니다: {TTL_PATH}")
        return {"label_to_uri": {}, "uri_to_type": {}}
    
    try:
        start_time = time.time()
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
            
            # 라벨 변형도 추가 (공백 제거, 괄호 내용 제거)
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri
            
            # 괄호 앞 부분만
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri
        
        load_time = time.time() - start_time
        print(f"📂 TTL 엔티티 로드 완료: {len(label_to_uri)}개 라벨, {len(uri_to_type)}개 타입 ({load_time:.2f}초)")
        
    except Exception as e:
        print(f"  ├─ [ERROR] TTL 파일 로드 실패: {e}")
    
    # 캐시 저장
    result = {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}
    _ttl_cache = result
    _ttl_cache_mtime = os.path.getmtime(TTL_PATH) if os.path.exists(TTL_PATH) else None
    
    return result


def match_entities_with_ttl(entities: list, ttl_data: dict) -> list:
    """
    추출된 엔티티를 TTL 데이터와 매칭
    
    Args:
        entities: LLM이 추출한 엔티티 리스트
        ttl_data: load_ttl_entities() 결과
    
    Returns:
        매칭된 엔티티 리스트 (URI 포함)
    """
    label_to_uri = ttl_data["label_to_uri"]
    uri_to_type = ttl_data["uri_to_type"]
    
    # 동의어 매핑 (질문에서 자주 사용되는 변형)
    SYNONYMS = {
        "복원": "복위",
        "복위": "복원",
        "역모": "역모사건",
        "사건": "",
        "의 난": "의난",
    }
    
    matched_entities = []
    
    for entity in entities:
        name = entity.get("name") or entity.get("value", "")
        entity_type = entity.get("type", "")
        
        # 1. 정확한 라벨 매칭
        if name in label_to_uri:
            uri = label_to_uri[name]
            matched_entities.append({
                "type": uri_to_type.get(uri, entity_type),
                "name": name,
                "uri": uri,
                "matched": True
            })
            continue
        
        # 2. 공백 제거 후 매칭
        clean_name = re.sub(r'\s+', '', name)
        if clean_name in label_to_uri:
            uri = label_to_uri[clean_name]
            matched_entities.append({
                "type": uri_to_type.get(uri, entity_type),
                "name": name,
                "uri": uri,
                "matched": True
            })
            continue
        
        # 3. 동의어 변환 후 매칭
        found = False
        normalized_name = clean_name
        for old, new in SYNONYMS.items():
            normalized_name = normalized_name.replace(old, new)
        
        if normalized_name in label_to_uri:
            uri = label_to_uri[normalized_name]
            matched_entities.append({
                "type": uri_to_type.get(uri, entity_type),
                "name": name,
                "uri": uri,
                "matched": True,
                "original_label": normalized_name
            })
            continue
        
        # 4. 부분 매칭 (라벨에 name이 포함된 경우)
        for label, uri in label_to_uri.items():
            if name in label or label in name:
                matched_entities.append({
                    "type": uri_to_type.get(uri, entity_type),
                    "name": name,
                    "uri": uri,
                    "matched": True,
                    "original_label": label
                })
                found = True
                break
        
        if found:
            continue
        
        # 5. 키워드 기반 매칭 (핵심 키워드로 검색)
        # "민비복원 사건" → "민비", "복원" → "민비복위" 매칭
        keywords = re.findall(r'[가-힣]{2,}', clean_name)
        best_match = None
        best_score = 0
        
        for label, uri in label_to_uri.items():
            score = 0
            label_clean = re.sub(r'\s+', '', label)
            
            # 키워드 매칭 점수 계산
            for kw in keywords:
                if kw in label_clean:
                    score += len(kw)
                # 동의어 변환 후 매칭
                for old, new in SYNONYMS.items():
                    kw_syn = kw.replace(old, new)
                    if kw_syn != kw and kw_syn in label_clean:
                        score += len(kw_syn)
            
            # 라벨의 핵심 키워드가 검색어에 있는지
            label_keywords = re.findall(r'[가-힣]{2,}', label_clean)
            for lkw in label_keywords:
                if lkw in clean_name:
                    score += len(lkw)
            
            if score > best_score:
                best_score = score
                best_match = (label, uri)
        
        # 최소 점수 이상이면 매칭
        if best_match and best_score >= 4:  # 최소 4글자 이상 매칭
            label, uri = best_match
            matched_entities.append({
                "type": uri_to_type.get(uri, entity_type),
                "name": name,
                "uri": uri,
                "matched": True,
                "original_label": label,
                "match_score": best_score
            })
            continue
        
        # 6. 매칭 실패 시에도 엔티티 유지 (SPARQL에서 label로 검색)
        matched_entities.append({
            "type": entity_type,
            "name": name,
            "uri": None,
            "matched": False
        })
    
    return matched_entities


# [DEPRECATED] kiwipiepy 형태소 분석기 사용으로 더 이상 필요 없음
# kiwipiepy가 없을 때만 fallback으로 사용 (현재는 사용 안 함)
def remove_particles(word: str) -> str:
    """
    [DEPRECATED] 한국어 조사/어미 제거 (하드코딩 규칙)
    
    [DEPRECATED] kiwipiepy 형태소 분석기를 사용하므로 이 함수는 더 이상 사용되지 않습니다.
    kiwipiepy가 없을 때만 fallback으로 사용됩니다.
    """
    # 간단한 fallback (kiwipiepy 없을 때만)
    if USE_KIWI:
        return word  # kiwipiepy 있으면 그대로 반환 (이미 처리됨)
    
    # 기본 조사만 제거 (최소한의 fallback)
    particles = ['을', '를', '이', '가', '은', '는', '에', '의', '와', '과', '로', '도', '만', '들']
    for p in particles:
        if word.endswith(p) and len(word) > len(p):
            return word[:-len(p)]
    return word


def extract_nouns_with_kiwi(query: str) -> list:
    """
    kiwipiepy 형태소 분석기로 명사만 추출
    
    품사 태그:
    - NNG: 일반명사
    - NNP: 고유명사 (인물, 지명 등)
    - NNB: 의존명사 (것, 수, 등)
    
    Args:
        query: 사용자 질문
        
    Returns:
        명사 리스트 (고유명사 우선)
    """
    if not USE_KIWI or _kiwi is None:
        return []
    
    try:
        tokens = _kiwi.tokenize(query)
        
        # 명사만 추출 (NNG: 일반명사, NNP: 고유명사)
        # 의존명사(NNB)는 제외 (것, 수, 등)
        nouns = []
        for token in tokens:
            if token.tag in ('NNG', 'NNP') and len(token.form) >= 2:
                nouns.append(token.form)
        
        return nouns
    except Exception as e:
        print(f"[ERROR] kiwipiepy 분석 실패: {e}")
        return []


def extract_keywords_from_query(query: str, for_vector_search: bool = False) -> list:
    """
    질문에서 키워드 추출 (kiwipiepy 형태소 분석기 사용)
    
    1. kiwipiepy 형태소 분석기로 명사 추출 (조사/어미 자동 제거)
    2. 불용어 제거
    3. 중복 제거
    
    Args:
        query: 사용자 질문
        for_vector_search: True면 벡터 검색용 (조선시대/조선 제외)
    
    Returns:
        키워드 리스트
    """
    # 불용어 (동사성 명사, 일반 명사)
    stopwords = {
        # 의문사/대명사
        '무엇', '누구', '어디', '언제', '무슨', '어떤',
        # 동사성 명사 (검색 노이즈)
        '건축', '건설', '설립', '창건', '조성', '설치', '시행', '실시',
        # 의존명사/일반명사
        '것', '수', '등', '때', '중', '후', '전', '이', '그', '저',
        '사실', '이유', '내용', '설명', '정보', '관련', '대해',
        # 시간 관련 (너무 일반적)
        '시대', '시기', '당시', '역사', '년', '월', '일',
        # 너무 일반적인 키워드 (모든 데이터에 포함됨)
        '조선', '조선시대', '조선왕조', '한국', '우리나라'
    }
    
    # 벡터 검색용 추가 필터 (모든 데이터가 조선시대라서 유사도가 다 높게 나옴)
    vector_search_exclude = {
        '조선', '조선시대', '조선왕조'
    }
    
    # ========================================
    # kiwipiepy 형태소 분석기로 명사 추출
    # ========================================
    if USE_KIWI:
        nouns = extract_nouns_with_kiwi(query)
        if nouns:
            # 불용어 제거
            keywords = [n for n in nouns if n not in stopwords]
            
            # 중복 제거 (순서 유지)
            seen = set()
            unique_keywords = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)
            
            # 벡터 검색용 필터링
            if for_vector_search:
                unique_keywords = [w for w in unique_keywords if w not in vector_search_exclude]
            
            return unique_keywords
    
    # ========================================
    # Fallback: kiwipiepy 없을 때만 (최소한의 처리)
    # ========================================
    print("[WARN] kiwipiepy 미설치 - 기본 키워드 추출 사용 (정확도 낮음)")
    
    # 한글 단어 추출 (2글자 이상)
    raw_words = re.findall(r'[가-힣]{2,}', query)
    
    # 간단한 조사 제거 (최소한)
    words_cleaned = [remove_particles(w) for w in raw_words]
    
    # 불용어 제거 + 1글자 제거
    keywords = [w for w in words_cleaned if w not in stopwords and len(w) >= 2]
    
    # 중복 제거
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    # 벡터 검색용 필터링
    if for_vector_search:
        unique_keywords = [w for w in unique_keywords if w not in vector_search_exclude]
    
    return unique_keywords


def extract_historical_keywords_with_llm(query: str, include_query_type: bool = False) -> dict:
    """
    LLM으로 역사적 키워드 + 질문 유형을 한 번에 추출 (LLM 호출 최적화)
    
    조사, 동사, 일반 단어를 제외하고 역사적 인물/사건/제도/장소만 추출
    
    Args:
        query: 사용자 질문
        include_query_type: True면 질문 유형도 함께 분류 (query_classifier 통합)
    
    Returns:
        {"keywords": [...], "query_type": "causal"} (include_query_type=True 시)
        또는 [...] (include_query_type=False 시)
    """
    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0
        )
        
        # 질문 유형 분류 포함 여부에 따라 프롬프트 분기
        if include_query_type:
            prompt = f"""다음 질문을 분석하세요.

## 질문
{query}

## 작업 1: 역사적 키워드 추출
- 역사적 인물명, 사건명, 제도/기관명, 장소명, 시대명만 추출
- 조사/동사/의문사/일반 단어 제외

## 작업 2: 질문 유형 분류
- causal: 인과관계/패턴 ("왜?", "영향은?", "결과는?", "패턴은?")
- deep_analysis: 심화 분석 ("진짜 이유?", "숨은 의도?", "이면에는?")

## 출력 형식 (JSON만, 다른 설명 없이)
{{"keywords": ["키워드1", "키워드2"], "query_type": "causal"}}

키워드가 없으면 빈 배열로 출력"""
        else:
            prompt = f"""다음 질문에서 **역사적 키워드만** 추출하세요.

## 질문
{query}

## 추출 규칙
1. 역사적 인물명 (예: 숙종, 명성황후, 이성계)
2. 역사적 사건명 (예: 경신환국, 왕자의 난, 을미사변)
3. 역사적 제도/기관명 (예: 비변사, 의금부)
4. 역사적 장소명 (예: 경덕궁, 경복궁)
5. 시대명/왕조명 (예: 조선시대, 고려)

## 제외 항목 (절대 추출하지 마세요)
- 조사: 의, 에, 를, 을, 은, 는, 이, 가, 대해서, 관련
- 동사: 알려줘, 있어, 했다, 되었다
- 의문사: 왜, 어떻게, 무엇, 언제
- 일반 단어: 사실, 이유, 진짜, 정말

## 출력 형식
쉼표로 구분된 키워드만 출력 (다른 설명 없이)
예: 명성황후, 을미사변, 경복궁

키워드가 없으면 빈 문자열 출력"""

        response = llm.invoke(prompt)
        
        # 토큰 사용량 추출 (state가 전달된 경우에만)
        # 이 함수는 state를 받지 않으므로, 호출하는 곳에서 토큰을 추출해야 함
        # 하지만 함수 시그니처를 변경하지 않고, 호출하는 곳에서 처리
        
        content = response.content.strip()
        
        # 파싱
        if include_query_type:
            # JSON 파싱
            import json
            try:
                # JSON 추출 (코드블록 제거)
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                result = json.loads(content)
                keywords = result.get("keywords", [])
                query_type = result.get("query_type", "causal")
                
                # 검증
                if query_type not in ["causal", "deep_analysis"]:
                    query_type = "causal"
                
                return {"keywords": keywords, "query_type": query_type}
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값
                return {"keywords": extract_keywords_from_query(query), "query_type": "causal"}
        else:
            if not content or content == "없음" or content == "없습니다":
                return []
            
            keywords = [kw.strip() for kw in content.split(',') if kw.strip()]
            
            # 추가 필터링 (혹시 모를 일반 단어 제거)
            stopwords = {'대해서', '대해', '관해서', '관해', '관련', '사실', '이유', 
                         '진짜', '정말', '어떻게', '무엇', '왜', '있어', '없어', 
                         '알려줘', '알려주세요', '알려', '하다', '되다'}
            keywords = [kw for kw in keywords if kw not in stopwords and len(kw) >= 2]
            
            return keywords
        
    except Exception as e:
        print(f"[ERROR] LLM 키워드 추출 실패: {e}")
        # 실패 시 기본 키워드 추출 사용
        if include_query_type:
            return {"keywords": extract_keywords_from_query(query), "query_type": "causal"}
        return extract_keywords_from_query(query)


def get_ttl_labels_by_type(ttl_data: dict) -> dict:
    """
    TTL 데이터에서 타입별 label 목록 추출 (LLM 프롬프트용)
    
    Returns:
        {"Person": ["숙종", "정조", ...], "Event": ["민비복위", ...], ...}
    """
    uri_to_type = ttl_data["uri_to_type"]
    label_to_uri = ttl_data["label_to_uri"]
    
    labels_by_type = {}
    for label, uri in label_to_uri.items():
        entity_type = uri_to_type.get(uri, "Unknown")
        if entity_type not in labels_by_type:
            labels_by_type[entity_type] = []
        labels_by_type[entity_type].append(label)
    
    return labels_by_type


# [REMOVED] expand_keywords_with_llm 함수 제거됨
# Stage 1-B에서 키워드 확장을 수행하므로 Stage 2에서는 백그라운드 확장이 불필요함

# [DEPRECATED] Fuseki 검색 제거됨 (TTL 매칭만 사용)
# def search_fuseki_with_keywords(keywords: list) -> list:
#     """
#     [DEPRECATED] Fuseki 검색 기능 제거됨
#     TTL 정확 매칭만 사용하여 엔티티 추출
#     """
#     pass


def search_entities_with_pgvector(keywords: list, ttl_data: dict, top_k: int = 5) -> list:
    """
    pgvector 제목 임베딩 유사도 검색으로 엔티티 찾기

    Args:
        keywords: 검색할 키워드 리스트
        ttl_data: TTL 데이터 (URI 매핑용)
        top_k: 키워드당 최대 결과 수

    Returns:
        매칭된 엔티티 리스트
    """
    title_vector_service = get_title_vector_service()
    if title_vector_service is None:
        return []

    entities = []
    seen_titles = set()

    try:
        # TitleVectorService 연결 확인 (lazy connection)
        if not title_vector_service.conn:
            if not title_vector_service.connect():
                print("[WARN] 제목 임베딩 pgvector 연결 실패")
                return []

        # 키워드로 벡터 검색
        query_text = " ".join(keywords)
        results = title_vector_service.search(query=query_text, top_k=top_k, threshold=0.5)

        for result in results:
            title = result["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # TTL에서 URI 찾기
            uri = ttl_data["label_to_uri"].get(title)
            entity_type = "Event"  # 기본값

            if uri:
                entity_type = ttl_data["uri_to_type"].get(uri, "Event")
            else:
                # category로 타입 추정
                category = result.get("category", "")
                type_map = {
                    "인물": "Person",
                    "사건": "Event",
                    "제도": "Institution",
                    "문헌": "Document",
                    "전투": "Battle",
                    "장소": "Place",
                    "물품": "Object"
                }
                entity_type = type_map.get(category, "Event")

            entities.append({
                "type": entity_type,
                "name": title,
                "uri": uri,
                "matched": uri is not None,
                "pgvector_score": result["similarity"],
                "matched_keyword": query_text
            })

        # 점수 순 정렬
        entities.sort(key=lambda x: x.get("pgvector_score", 0), reverse=True)

    except Exception as e:
        print(f"[ERROR] 제목 임베딩 pgvector 검색 실패: {e}")

    return entities


def entity_expander_node(state: GraphState) -> GraphState:
    """
    질문에서 핵심 엔티티 추출 (하이브리드 방식)

    키워드 추출 + pgvector 제목 임베딩 유사도 검색을 병렬로 수행
    - 1단계: 키워드 추출 (kiwipiepy)
    - 2단계: 키워드 확장 (classify_node에서 처리된 확장된 키워드 사용)
    - 3단계: TTL 정확 매칭 (확장된 키워드 + 원본 키워드 모두 사용)
    - 4단계: pgvector 제목 임베딩 유사도 검색 (fallback)
    - 5단계: LLM 엔티티 추출 (최종 fallback - 결과 부족 시만)

    의도 파악: classify_node에서 이미 처리됨 (query_intent)
    """

    import time
    node_start = time.time()

    query = state.get("query", "")

    print(f"\n{'='*70}")
    print(f"[Stage 2/6] 엔티티 추출 (Entity Extractor)")
    print(f"{'='*70}")

    # Phase 1: 사용자 선택 방향 확인
    user_selected_direction = state.get("user_selected_direction")
    expansion_directions = state.get("expansion_directions", [])
    selected_direction_info = None

    if user_selected_direction and expansion_directions:
        # 선택된 방향 정보 찾기
        for direction in expansion_directions:
            if direction["direction_id"] == user_selected_direction:
                selected_direction_info = direction
                break

        if selected_direction_info:
            print(f"  ├─ 선택된 방향: {selected_direction_info['title']}")
            print(f"  ├─ 우선 Property Groups: {', '.join(selected_direction_info.get('property_groups', [])[:3])}")

    # 1. TTL 데이터 로드 (캐싱됨)
    ttl_data = load_ttl_entities()

    # 2. 키워드 추출 (kiwipiepy) - classify_node에서 이미 추출됨, 재사용 가능
    query_keywords = extract_keywords_from_query(query, for_vector_search=False)

    # 3. 키워드 확장 처리 (Stage 1-B 결과 사용)
    # Stage 2부터 시작하는 경우 Stage 1-B 백그라운드 작업 완료 대기
    expanded_keywords_from_classify = state.get("expanded_keywords", [])
    expanded_keywords_dict = state.get("expanded_keywords_dict", {})

    if not expanded_keywords_from_classify:
        # Stage 1-B 결과가 없는 경우 백그라운드 작업 확인 및 대기
        stage1b_task_id = state.get("stage1b_task_id")
        if stage1b_task_id:
            print(f"  ├─ Stage 1-B 백그라운드 작업 대기 중... (task_id={stage1b_task_id})")
            from backend.langgraph_fuseki.utils.clarification_utils import get_stage1b_result
            stage1b_result = get_stage1b_result(stage1b_task_id, True, state, timeout=60)
            
            if stage1b_result.get("status") == "success":
                expanded_keywords_from_classify = stage1b_result.get("expanded_keywords", [])
                expanded_keywords_dict = stage1b_result.get("expanded_keywords_dict", {})
                print(f"  ├─ Stage 1-B 백그라운드 결과 수신: {len(expanded_keywords_from_classify)}개 키워드")
                
                # state에 결과 저장 (다음 노드들이 사용할 수 있도록)
                state["expanded_keywords"] = expanded_keywords_from_classify
                state["expanded_keywords_dict"] = expanded_keywords_dict
                if stage1b_result.get("query_type"):
                    state["query_type"] = stage1b_result["query_type"]
                if stage1b_result.get("selected_property_groups"):
                    state["selected_property_groups"] = stage1b_result["selected_property_groups"]
                    state["selected_properties"] = stage1b_result.get("selected_properties", [])
            else:
                print(f"  ├─ [WARN] Stage 1-B 백그라운드 실패: {stage1b_result.get('status', 'unknown')}")

    if expanded_keywords_from_classify:
        # Stage 1-B에서 이미 확장됨 (즉시 사용)
        print(f"  ├─ Stage 1-B 확장 키워드 사용: {len(expanded_keywords_from_classify)}개")
        expanded_keywords = expanded_keywords_from_classify
    else:
        # Stage 1-B 결과가 없는 경우 (비정상 상황)
        print(f"  ├─ [WARN] Stage 1-B 확장 키워드 없음, 기본 키워드만 사용: {len(query_keywords)}개")
        expanded_keywords = query_keywords.copy()

    # 원본 키워드와 확장된 키워드 병합
    all_keywords = list(set(query_keywords + expanded_keywords))

    # query_type은 query_classifier_node에서 이미 설정됨
    current_query_type = state.get("query_type", "causal")

    matched_entities = []
    seen = set()

    # 키워드 기반 엔티티 점수 계산을 위한 함수
    def calculate_entity_base_score(entity, keywords, ttl_data):
        """
        엔티티와 키워드의 기본 연관성 점수 계산 (SPARQL 제외)
        
        Args:
            entity: 엔티티 딕셔너리 (name, uri, type 포함)
            keywords: 키워드 리스트
            ttl_data: TTL 데이터 (uri_to_type 포함)
        
        Returns:
            계산된 점수 (float)
        """
        # 1. 기본 점수 (엔티티 타입별 가중치)
        entity_type = entity.get("type", "Unknown")
        type_weights = {
            "Person": 1.0,
            "Event": 0.9,
            "Place": 0.8,
            "Institution": 0.7,
            "Document": 0.6,
            "Policy": 0.5,
            "Object": 0.4
        }
        base_score = type_weights.get(entity_type, 0.3)

        # 2. 이름 매칭 점수 (부분 일치)
        name = entity.get("name", "").lower()
        name_match_score = sum(0.5 for kw in keywords if kw.lower() in name)

        # SPARQL 연결 점수는 별도 처리
        total_score = base_score + name_match_score
        entity["relevance_score"] = total_score
        return total_score

    # 키워드 기반 엔티티 점수 계산을 위한 함수
    def calculate_entity_score_with_connections(entity, keywords, ttl_data):
        """
        엔티티와 키워드의 연관성 점수 계산

        점수 구성:
        1. 매칭 방법 기본 점수: exact(1.0), partial(0.7), milvus(유사도), llm(0.3)
        2. 엔티티 이름에 키워드 포함: +0.5/keyword
        3. 연결된 노드에 키워드 포함: +0.1/connection (최대 0.3)
        """
        # 1. 기본 점수
        match_method = entity.get("match_method", "exact")
        base_score = {
            "exact": 1.0,
            "partial": 0.7,
            "llm": 0.3
        }.get(match_method, entity.get("milvus_score", 0.5))

        # 2. 이름에 키워드 포함 점수
        name = entity.get("name", "").lower()
        name_match_score = sum(0.5 for kw in keywords if kw.lower() in name)

        # 3. 연결된 노드에 키워드 포함 점수 (SPARQL 기반)
        connected_score = 0.0
        uri = entity.get("uri")
        sparql_executed = False
        connection_count = 0

        if uri and uri in ttl_data.get("uri_to_type", {}):
            # SPARQL로 이 엔티티와 연결된 모든 엔티티의 label 조회
            # (양방향: 나가는 관계 + 들어오는 관계)
            # URI 형식 변환: hist:Person_7c2da48e → http://www.example.org/korean-history#Person_7c2da48e
            full_uri = uri.replace("hist:", "http://www.example.org/korean-history#")
            
            sparql_query = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT DISTINCT ?connectedLabel WHERE {{
                    {{
                        # 나가는 관계 (이 엔티티 → 다른 엔티티)
                        <{full_uri}> ?p ?connected .
                        ?connected rdfs:label ?connectedLabel .
                        FILTER(?p != rdf:type)
                        FILTER(?p != rdfs:label)
                    }}
                    UNION
                    {{
                        # 들어오는 관계 (다른 엔티티 → 이 엔티티)
                        ?connected ?p <{full_uri}> .
                        ?connected rdfs:label ?connectedLabel .
                        FILTER(?p != rdf:type)
                        FILTER(?p != rdfs:label)
                    }}
                }} LIMIT 50
            """

            try:
                fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")

                results = execute_sparql_query(fuseki_url, sparql_query, timeout=5)
                if results:
                    sparql_executed = True
                    bindings = results.get("results", {}).get("bindings", [])
                    connection_count = len(bindings)

                    # 연결된 엔티티의 label에 키워드가 있는지 확인
                    matched_connections = []
                    has_keyword_match = False  # 키워드 매칭 여부 플래그
                    for binding in bindings:
                        connected_label = binding.get("connectedLabel", {}).get("value", "")
                        if connected_label:
                            for kw in keywords:
                                if kw.lower() in connected_label.lower():
                                    connected_score += 0.1
                                    matched_connections.append(connected_label)
                                    has_keyword_match = True  # 키워드 매칭 발견
                                    if connected_score >= 0.3:  # 최대값 도달
                                        break

                        if connected_score >= 0.3:
                            break

                    # 연결 노드 분석 결과 저장
                    entity["sparql_connections"] = connection_count
                    entity["matched_connections"] = len(matched_connections)
                    entity["has_keyword_in_connections"] = has_keyword_match  # 우선순위 정렬용 플래그
                    
                    # 간소화된 로그 (연결이 있을 때만)
                    if connection_count > 0:
                        print(f"  │   ✓ {entity.get('name', 'Unknown')}: {connection_count}개 연결 (매칭: {len(matched_connections)})")
                    
                else:
                    print(f"    [ERROR] SPARQL 쿼리 실패: HTTP {response.status_code}")

            except requests.exceptions.Timeout:
                print(f"    [ERROR] SPARQL 타임아웃: {entity.get('name')} ({uri})")
            except requests.exceptions.ConnectionError:
                print(f"    [ERROR] SPARQL 연결 실패: Fuseki 서버 확인 필요 ({fuseki_url})")
            except Exception as e:
                print(f"    [ERROR] SPARQL 예외: {entity.get('name')} - {str(e)}")

        # 디버깅 정보 저장
        entity["sparql_executed"] = sparql_executed
        
        # 연결된 노드에 키워드가 없는 경우 플래그 설정
        if "has_keyword_in_connections" not in entity:
            entity["has_keyword_in_connections"] = False

        total_score = base_score + name_match_score + min(connected_score, 0.3)
        entity["relevance_score"] = total_score
        return total_score
    
    # ========================================
    # TTL 정확 매칭 (Fuseki 검색 제거)
    # ========================================
    
    # 벡터 검색용 키워드 (조선시대/조선 제외)
    vector_keywords = extract_keywords_from_query(query, for_vector_search=True)
    
    # --- TTL 정확 매칭 (확장된 키워드 + 원본 키워드 사용) ---
    print(f"  ├─ TTL 매칭 중...")
    ttl_matched = 0

    # 모든 키워드로 TTL 매칭 (확장된 키워드 + 원본 키워드)
    for keyword in all_keywords:
        # 정확한 라벨 매칭
        if keyword in ttl_data["label_to_uri"]:
            uri = ttl_data["label_to_uri"][keyword]
            entity_type = ttl_data["uri_to_type"].get(uri, "Event")
            key = uri or keyword
            if key not in seen:
                seen.add(key)
                matched_entities.append({
                    "type": entity_type,
                    "name": keyword,
                    "uri": uri,
                    "matched": True,
                    "match_method": "exact"
                })
                ttl_matched += 1

        # 부분 매칭 (키워드가 라벨에 포함된 경우) - 최대 3개, 최소 길이 3글자
        # "조선" 같은 일반 키워드 필터링 강화
        if len(keyword) >= 3:  # 3글자 이상만 부분 매칭
            partial_count = 0
            for label, uri in ttl_data["label_to_uri"].items():
                if keyword in label:
                    key = uri or label
                    if key not in seen:
                        seen.add(key)
                        entity_type = ttl_data["uri_to_type"].get(uri, "Event")
                        matched_entities.append({
                            "type": entity_type,
                            "name": label,
                            "uri": uri,
                            "matched": True,
                            "match_method": "partial",
                            "matched_keyword": keyword
                        })
                        ttl_matched += 1
                        partial_count += 1
                        if partial_count >= 3:  # 키워드당 최대 3개 부분 매칭 (성능 최적화)
                            break

    print(f"  │  └─ TTL 매칭: {ttl_matched}개")

    # 최종 TTL 매칭 개수 업데이트
    ttl_matched = len([e for e in matched_entities if e.get("match_method", "").startswith("exact")])

    # --- pgvector 제목 임베딩 유사도 검색 (규칙 기반 키워드 사용) ---
    # [REFACTOR] 리팩토링: LLM 대신 규칙 기반 키워드로 벡터 검색
    # - "조선시대/조선" 제외 (모든 데이터가 조선시대라서)
    # - 조사/동사 제거된 명확한 단어만 사용
    pgvector_added = 0
    if USE_PGVECTOR and vector_keywords:
        print(f"  ├─ pgvector 제목 임베딩 벡터 검색 중...")

        # 동적 top_k: 키워드 수에 따라 조절
        dynamic_top_k = max(3, min(10, 15 // max(len(vector_keywords), 1)))

        # 규칙 기반으로 추출된 키워드로 pgvector 검색
        pgvector_entities = search_entities_with_pgvector(
            vector_keywords,  # 조선시대/조선 제외된 키워드
            ttl_data,
            top_k=dynamic_top_k
        )

        # 기존에 없는 엔티티만 추가
        for e in pgvector_entities:
            key = e.get("uri") or e.get("name")
            if key not in seen:
                seen.add(key)
                e["match_method"] = "pgvector"
                matched_entities.append(e)
                pgvector_added += 1

        print(f"  │  └─ pgvector 추가: {pgvector_added}개")
    
    # ========================================
    # 3단계: LLM 엔티티 추출 (결과가 부족할 때만)
    # ========================================
    if len(matched_entities) < 3:
        print(f"\n  ├─ LLM 엔티티 추출 중...")
        
        # TTL label 목록 준비
        labels_by_type = get_ttl_labels_by_type(ttl_data)
        
        # 키워드와 관련된 label만 필터링
        relevant_labels = {}
        for entity_type, labels in labels_by_type.items():
            filtered = [label for label in labels 
                       if any(kw in label for kw in query_keywords)]
            if not filtered:
                filtered = labels[:15]
            else:
                filtered = filtered[:20]
            relevant_labels[entity_type] = filtered
        
        # TTL label 목록 문자열 생성
        ttl_label_list = []
        for entity_type in ["Event", "Person", "Institution", "Document", "Battle", "Place"]:
            labels = relevant_labels.get(entity_type, [])
            if labels:
                ttl_label_list.append(f"[{entity_type}] {', '.join(labels[:10])}")
        
        ttl_labels_str = "\n".join(ttl_label_list)
        
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0
        )

        extraction_prompt = f"""당신은 조선시대 역사 데이터에서 엔티티를 추출하는 전문가입니다.

## 실제 데이터베이스에 존재하는 엔티티 목록:
{ttl_labels_str}

## 질문:
{query}

## 작업:
1. 위 질문에서 언급된 역사적 엔티티를 추출하세요
2. **반드시 위 "실제 데이터베이스" 목록에서 가장 유사한 엔티티명을 선택**하세요

## 출력 형식 (JSON 배열만):
[{{"type": "Event", "name": "엔티티명"}}]

## 규칙:
- 목록에 있는 정확한 이름 사용
- 관련 엔티티가 없으면 빈 배열 [] 반환
- JSON만 출력"""

        try:
            response = llm.invoke(extraction_prompt)
            
            # 토큰 사용량 추출 및 state에 누적
            token_update = extract_and_accumulate_tokens(state, response)
            state.update(token_update)
            
            content = response.content.strip()
            
            # JSON 파싱
            if "```" in content:
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
            
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            llm_entities = json.loads(content)
            
            if isinstance(llm_entities, list):
                for e in llm_entities:
                    if isinstance(e, dict) and e.get("name"):
                        name = e["name"]
                        uri = ttl_data["label_to_uri"].get(name)
                        entity_type = e.get("type", "Event")
                        
                        if uri:
                            entity_type = ttl_data["uri_to_type"].get(uri, entity_type)
                        
                        key = uri or name
                        if key not in seen:
                            seen.add(key)
                            matched_entities.append({
                                "type": entity_type,
                                "name": name,
                                "uri": uri,
                                "matched": uri is not None,
                                "match_method": "llm"
                            })
            
            print(f"      → LLM 추가: {len(llm_entities)}개")
            
        except Exception as e:
            print(f"[ERROR] LLM 추출 실패: {e}")
    
    # ========================================
    # 엔티티 점수 계산 및 정렬
    # ========================================
    print(f"  ├─ SPARQL 기반 스코어링 중...")

    # 모든 엔티티에 대해 점수 계산 (배치 처리 시도)
    sparql_count = 0
    total_connections = 0
    total_matched_connections = 0

    # 성능 최적화: SPARQL 배치 처리 시도
    config = get_performance_config()
    if config and len(matched_entities) > config.sparql_batch_size:
        try:
            from backend.langgraph_fuseki.utils.performance_optimizer import BatchSPARQLExecutor
            fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
            executor = BatchSPARQLExecutor(fuseki_url, config)
            
            print(f"  │  ├─ SPARQL 배치 처리 시작 ({len(matched_entities)}개 엔티티)")
            
            # 기본 점수 계산 (SPARQL 제외)
            for entity in matched_entities:
                calculate_entity_base_score(entity, all_keywords, ttl_data)
            
            # SPARQL 연결 배치 처리
            matched_entities = executor.process_entities_batch(matched_entities, all_keywords)
            
            print(f"  │  └─ SPARQL 배치 처리 완료")
            
        except ImportError:
            print(f"  │  ├─ 성능 최적화 모듈 없음, 순차 처리")
            # 기존 방식으로 폴백
            for entity in matched_entities:
                calculate_entity_score_with_connections(entity, all_keywords, ttl_data)
    else:
        # 엔티티가 적거나 최적화 설정이 없으면 기존 방식
        for entity in matched_entities:
            calculate_entity_score_with_connections(entity, all_keywords, ttl_data)

    # SPARQL 통계 계산
    for entity in matched_entities:
        if entity.get("sparql_executed"):
            sparql_count += 1
            total_connections += entity.get("sparql_connections", 0)
            total_matched_connections += entity.get("matched_connections", 0)

    # SPARQL 스코어링 통계 출력
    if sparql_count > 0:
        avg_connections = total_connections / sparql_count if sparql_count > 0 else 0
        print(f"  │  └─ SPARQL 스코어링: {sparql_count}개 엔티티, 평균 연결노드 {avg_connections:.1f}개, 키워드 매칭 {total_matched_connections}개")
    else:
        print(f"  │  └─ SPARQL 스코어링: 실행되지 않음")

    # 정렬: 키워드가 연결된 노드에 있는 엔티티를 우선적으로, 그 다음 점수 기준
    # 1순위: has_keyword_in_connections (True가 먼저)
    # 2순위: relevance_score (높은 점수 우선)
    matched_entities.sort(
        key=lambda x: (
            not x.get("has_keyword_in_connections", False),  # False가 먼저 오도록 (True를 우선)
            -x.get("relevance_score", 0)  # 내림차순 정렬을 위해 음수
        )
    )

    # 상위 30개만 선택 (너무 많으면 성능 저하)
    matched_entities = matched_entities[:30]

    # ========================================
    # 결과 정리
    # ========================================
    ontology_schema = get_schema_summary()

    # 추출된 엔티티 상세 목록 (상위 10개)
    if matched_entities:
        print(f"  │\n  │   [추출된 엔티티 상세]")
        for i, entity in enumerate(matched_entities[:10], 1):
            name = entity.get("name", "")
            entity_type = entity.get("type", "Unknown")
            method = entity.get("match_method", "")
            relevance_score = entity.get("relevance_score", 0)
            milvus_score = entity.get("milvus_score")

            # 매칭 방법 레이블
            method_label = "[정확]" if method == "exact" else "[부분]" if method == "partial" else "[벡터]" if method in ["milvus", "pgvector"] else "[LLM]"

            # 점수 표시 (연관성 점수 우선, Milvus 점수는 참고용)
            if milvus_score:
                score_str = f" (점수: {relevance_score:.2f}, 벡터: {milvus_score:.2f})"
            else:
                score_str = f" (점수: {relevance_score:.2f})"

            print(f"  │   {i:2d}. {method_label:6s} [{entity_type:12s}] {name}{score_str}")

        if len(matched_entities) > 10:
            print(f"      ... 외 {len(matched_entities) - 10}개")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {len(matched_entities)}개 엔티티 추출 (TTL: {ttl_matched}, pgvector: {pgvector_added}) ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["entity_expander"] = node_elapsed

    # Phase 1: 최종 query_type 확정
    # 사용자 선택에 따라 query_type이 변경될 수 있음
    final_query_type = state.get("query_type_initial", "causal")

    # 선택된 방향에 따라 query_type 조정 (Phase 1에서는 대부분 유지)
    if selected_direction_info:
        # 예: long_term_impact 선택 시 deep_analysis로 변경
        direction_id = selected_direction_info.get("direction_id", "")
        if "impact" in direction_id or "scope" in direction_id:
            # 영향/범위 관련은 deep_analysis로 처리
            if state.get("query_type_initial") == "causal":
                final_query_type = "deep_analysis"

    # 최종 상태 업데이트
    state["extracted_entities"] = matched_entities
    state["ontology_schema"] = ontology_schema
    state["ttl_data"] = ttl_data
    state["query_type"] = final_query_type  # 최종 확정
    
    # 키워드 확장 추적 정보 저장 (state 레벨에서만 관리)
    keyword_expansion_trace = {
        "initial_keywords": query_keywords,
        "expanded_keywords": expanded_keywords if expanded_keywords != query_keywords else [],
        "expansion_method": "classify_node",
        "expansion_successful": len(expanded_keywords) > len(query_keywords)
    }
    state["keyword_expansion_trace"] = keyword_expansion_trace
    
    # 엔티티별 키워드 매칭 정보 저장
    for entity in matched_entities:
        # 어떤 키워드에서 추출되었는지 추적
        entity_name = entity.get("name", "")
        matched_keyword = None
        is_from_expansion = False
        
        # 기본 키워드에서 매칭 확인
        for kw in query_keywords:
            if kw in entity_name or entity_name in kw:
                matched_keyword = kw
                is_from_expansion = False
                break
        
        # 확장 키워드에서 매칭 확인 (기본 키워드에서 매칭되지 않은 경우)
        if not matched_keyword:
            for kw in expanded_keywords:
                if kw not in query_keywords and (kw in entity_name or entity_name in kw):
                    matched_keyword = kw
                    is_from_expansion = True
                    break
        
        # 매칭 정보 저장
        entity["keyword_trace"] = {
            "matched_keyword": matched_keyword or entity.get("matched_keyword", ""),
            "is_from_expansion": is_from_expansion,
            "expansion_method": "llm_expansion" if is_from_expansion else "initial_extraction"
        }
    
    state["executed_nodes"] = state.get("executed_nodes", []) + ["entity_expander"]
    
    # 노드 실행 시간 기록 (기존 시간들 유지)
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["entity_expander"] = node_elapsed

    return state
