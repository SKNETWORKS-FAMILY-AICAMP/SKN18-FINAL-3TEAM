"""
Entity Extractor Node

질문에서 핵심 엔티티 추출 및 TTL 데이터 매칭:
1. 키워드 추출 → TTL 정확 매칭 (빠름)
2. Milvus 유사도 검색 (fallback)
3. LLM 엔티티 추출 (최종 fallback)
4. 엔티티 URI 반환

+ 추출된 엔티티 타입에 맞는 온톨로지 스키마 정보 제공
"""

import os
import sys
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from state import GraphState
from ontology_schema import get_schema_summary

# Milvus 서비스 import (선택적)
USE_MILVUS = os.getenv("USE_MILVUS", "true").lower() == "true"
_milvus_service = None

def get_milvus_service():
    """Milvus 서비스 lazy loading"""
    global _milvus_service
    if _milvus_service is None and USE_MILVUS:
        try:
            from db_pipeline.services.milvus_service import get_milvus_service as _get_milvus
            _milvus_service = _get_milvus()
            if not _milvus_service.connect():
                print("⚠️ Milvus 연결 실패 - TTL 매칭만 사용")
                _milvus_service = None
        except ImportError:
            print("⚠️ Milvus 서비스 import 실패 - TTL 매칭만 사용")
        except Exception as e:
            print(f"⚠️ Milvus 초기화 실패: {e}")
    return _milvus_service


# TTL 파일 경로 (normalized 버전 사용 - Fuseki에 업로드된 데이터와 일치)
TTL_PATH = Path(__file__).parent.parent / "ontology/instances/korean_history_normalized.ttl"


def load_ttl_entities() -> dict:
    """
    TTL 파일에서 모든 엔티티와 label 로드
    
    Returns:
        {
            "label_to_uri": {"심기원역모사건": "hist:Event_심기원역모사건", ...},
            "uri_to_type": {"hist:Event_심기원역모사건": "Event", ...}
        }
    """
    label_to_uri = {}
    uri_to_type = {}
    
    if not TTL_PATH.exists():
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
            
            # 라벨 변형도 추가 (공백 제거, 괄호 내용 제거)
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri
            
            # 괄호 앞 부분만
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri
        
        print(f"📂 TTL 엔티티 로드 완료: {len(label_to_uri)}개 라벨, {len(uri_to_type)}개 타입")
        
    except Exception as e:
        print(f"⚠️ TTL 파일 로드 실패: {e}")
    
    return {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}


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


def extract_keywords_from_query(query: str) -> list:
    """
    질문에서 키워드 직접 추출 (LLM 실패 시 fallback)
    
    Args:
        query: 사용자 질문
    
    Returns:
        키워드 리스트
    """
    # 불용어 제거
    stopwords = {'이', '가', '은', '는', '을', '를', '에', '의', '와', '과', '로', '으로', 
                 '에서', '까지', '부터', '에게', '한테', '께', '보다', '처럼', '만큼',
                 '어떤', '무엇', '왜', '어떻게', '언제', '누구', '어디', '무슨',
                 '있다', '없다', '하다', '되다', '이다', '아니다',
                 '그', '저', '이', '것', '수', '등', '때', '중', '후', '전'}
    
    # 한글 단어 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}', query)
    
    # 불용어 제거
    keywords = [w for w in words if w not in stopwords]
    
    return keywords


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


def search_entities_with_milvus(keywords: list, ttl_data: dict, top_k: int = 5) -> list:
    """
    Milvus 유사도 검색으로 엔티티 찾기
    
    Args:
        keywords: 검색할 키워드 리스트
        ttl_data: TTL 데이터 (URI 매핑용)
        top_k: 키워드당 최대 결과 수
    
    Returns:
        매칭된 엔티티 리스트
    """
    milvus = get_milvus_service()
    if milvus is None:
        return []
    
    entities = []
    seen_titles = set()
    
    try:
        # 키워드별로 유사도 검색
        for keyword in keywords:
            results = milvus.search(keyword, top_k=top_k, threshold=0.5)
            
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
                    "milvus_score": result["score"],
                    "matched_keyword": keyword
                })
        
        # 점수 순 정렬
        entities.sort(key=lambda x: x.get("milvus_score", 0), reverse=True)
        
    except Exception as e:
        print(f"⚠️ Milvus 검색 실패: {e}")
    
    return entities


def entity_extractor_node(state: GraphState) -> GraphState:
    """
    질문에서 핵심 엔티티 추출 (하이브리드 방식)
    
    1단계: 키워드 추출 → TTL 정확 매칭 (빠름)
    2단계: Milvus 유사도 검색 (fallback)
    3단계: LLM 엔티티 추출 (최종 fallback)
    """

    query = state.get("query", "")
    print(f"\n🔍 엔티티 추출 중... (질문: {query[:50]}...)")

    # 1. TTL 데이터 로드
    ttl_data = load_ttl_entities()
    
    # 2. 키워드 추출
    query_keywords = extract_keywords_from_query(query)
    print(f"   📝 추출된 키워드: {query_keywords}")
    
    matched_entities = []
    
    # ========================================
    # 1단계: TTL 정확 매칭 (키워드 기반)
    # ========================================
    print(f"\n   🎯 1단계: TTL 정확 매칭...")
    
    for keyword in query_keywords:
        # 정확한 라벨 매칭
        if keyword in ttl_data["label_to_uri"]:
            uri = ttl_data["label_to_uri"][keyword]
            entity_type = ttl_data["uri_to_type"].get(uri, "Event")
            matched_entities.append({
                "type": entity_type,
                "name": keyword,
                "uri": uri,
                "matched": True,
                "match_method": "exact"
            })
            continue
        
        # 부분 매칭 (키워드가 라벨에 포함된 경우)
        for label, uri in ttl_data["label_to_uri"].items():
            if keyword in label and len(keyword) >= 2:
                entity_type = ttl_data["uri_to_type"].get(uri, "Event")
                matched_entities.append({
                    "type": entity_type,
                    "name": label,
                    "uri": uri,
                    "matched": True,
                    "match_method": "partial",
                    "matched_keyword": keyword
                })
    
    # 중복 제거
    seen = set()
    unique_entities = []
    for e in matched_entities:
        key = e.get("uri") or e.get("name")
        if key not in seen:
            seen.add(key)
            unique_entities.append(e)
    matched_entities = unique_entities
    
    print(f"      → TTL 매칭: {len(matched_entities)}개")
    
    # ========================================
    # 2단계: Milvus 유사도 검색 (추가 엔티티 발굴)
    # ========================================
    if USE_MILVUS and len(matched_entities) < 10:
        print(f"\n   🔮 2단계: Milvus 유사도 검색...")
        
        milvus_entities = search_entities_with_milvus(query_keywords, ttl_data, top_k=5)
        
        # 기존에 없는 엔티티만 추가
        for e in milvus_entities:
            key = e.get("uri") or e.get("name")
            if key not in seen:
                seen.add(key)
                e["match_method"] = "milvus"
                matched_entities.append(e)
        
        print(f"      → Milvus 추가: {len(milvus_entities)}개")
    
    # ========================================
    # 3단계: LLM 엔티티 추출 (결과가 부족할 때만)
    # ========================================
    if len(matched_entities) < 3:
        print(f"\n   🤖 3단계: LLM 엔티티 추출...")
        
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
            print(f"      ⚠️ LLM 추출 실패: {e}")
    
    # ========================================
    # 결과 정리
    # ========================================
    print(f"\n🔍 추출된 엔티티: {len(matched_entities)}개")
    matched_count = sum(1 for e in matched_entities if e.get("matched"))
    unmatched_count = len(matched_entities) - matched_count
    
    if matched_entities:
        for i, entity in enumerate(matched_entities[:10], 1):  # 최대 10개만 출력
            name = entity.get("name", "")
            entity_type = entity.get("type", "")
            uri = entity.get("uri", "")
            method = entity.get("match_method", "")
            score = entity.get("milvus_score", "")
            status = "✅" if entity.get("matched") else "⚠️"
            
            score_str = f" (유사도: {score:.2f})" if score else ""
            print(f"   {i}. {status} [{entity_type}] {name} [{method}]{score_str}")
            if uri:
                print(f"      → URI: {uri}")
    else:
        print("   ⚠️ 엔티티가 추출되지 않았습니다.")
    
    print(f"   📊 매칭 성공: {matched_count}개, 미매칭: {unmatched_count}개")

    # 온톨로지 스키마 정보 가져오기
    ontology_schema = get_schema_summary()

    print(f"\n📐 온톨로지 스키마:")
    print(f"   - 클래스: {', '.join(ontology_schema['classes'])}")

    # 추출된 엔티티 타입에 해당하는 속성만 출력
    entity_types = list(set([e.get("type", "") for e in matched_entities if e.get("type")]))
    if entity_types:
        print(f"   - 추출된 타입의 속성:")
        for entity_type in entity_types:
            props = ontology_schema["properties_by_class"].get(entity_type, [])
            if props:
                print(f"     • {entity_type}: {len(props)}개 ({', '.join(props[:3])}...)")

    return {
        **state,
        "extracted_entities": matched_entities,
        "ontology_schema": ontology_schema,
        "ttl_data": ttl_data,
        "executed_nodes": state.get("executed_nodes", []) + ["entity_extractor"]
    }
