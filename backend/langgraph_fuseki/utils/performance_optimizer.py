"""
LangGraph 성능 최적화 유틸리티

Entity Expander Node의 성능을 향상시키기 위한 최적화 도구들:
1. TTL 데이터 병렬 로딩
2. SPARQL 쿼리 배치 처리
3. 벡터 검색 지연 로딩
4. 스마트 캐싱
"""

import os
import re
import time
import asyncio
import aiohttp
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PerformanceConfig:
    """성능 최적화 설정"""
    # 병렬 처리 설정
    max_workers: int = 4
    sparql_batch_size: int = 10
    
    # 타임아웃 설정
    sparql_timeout: int = 3
    vector_search_timeout: int = 5
    
    # 캐시 설정
    enable_ttl_cache: bool = True
    enable_vector_cache: bool = True
    
    # 지연 로딩 설정
    lazy_load_vectors: bool = True


class OptimizedTTLLoader:
    """최적화된 TTL 로더 - LangGraph용"""
    
    def __init__(self, ttl_path: str, config: PerformanceConfig = None):
        self.ttl_path = ttl_path
        self.config = config or PerformanceConfig()
        self._cache = None
        self._cache_mtime = None
    
    def load_entities_parallel(self) -> Dict[str, Any]:
        """
        TTL 파일을 병렬로 파싱하여 엔티티 로드
        
        Returns:
            {
                "label_to_uri": {...},
                "uri_to_type": {...},
                "load_time": float
            }
        """
        start_time = time.time()
        
        # 캐시 확인
        if self.config.enable_ttl_cache and self._is_cache_valid():
            return self._cache
        
        if not os.path.exists(self.ttl_path):
            print(f"[WARN] TTL 파일이 없습니다: {self.ttl_path}")
            return {"label_to_uri": {}, "uri_to_type": {}, "load_time": 0}
        
        # 파일을 청크로 분할하여 병렬 처리
        with open(self.ttl_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 파일을 여러 청크로 분할
        chunk_size = len(content) // self.config.max_workers
        chunks = []
        
        for i in range(self.config.max_workers):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < self.config.max_workers - 1 else len(content)
            
            # 청크 경계를 줄바꿈으로 조정
            if i > 0:
                while start_idx < len(content) and content[start_idx] != '\n':
                    start_idx += 1
                start_idx += 1
            
            if end_idx < len(content):
                while end_idx < len(content) and content[end_idx] != '\n':
                    end_idx += 1
            
            chunks.append(content[start_idx:end_idx])
        
        # 병렬 파싱
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = [executor.submit(self._parse_chunk, chunk) for chunk in chunks]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 결과 병합
        label_to_uri = {}
        uri_to_type = {}
        
        for result in results:
            label_to_uri.update(result["label_to_uri"])
            uri_to_type.update(result["uri_to_type"])
        
        load_time = time.time() - start_time
        
        result = {
            "label_to_uri": label_to_uri,
            "uri_to_type": uri_to_type,
            "load_time": load_time
        }
        
        # 캐시 저장
        if self.config.enable_ttl_cache:
            self._cache = result
            self._cache_mtime = os.path.getmtime(self.ttl_path)
        
        print(f"  │   ✓ TTL 병렬 로딩: {len(label_to_uri)}개 라벨, {len(uri_to_type)}개 타입 ({load_time:.2f}초)")
        
        return result
    
    def _parse_chunk(self, chunk: str) -> Dict[str, Dict[str, str]]:
        """TTL 청크 파싱"""
        label_to_uri = {}
        uri_to_type = {}
        
        # 타입 추출
        type_pattern = r'(hist:\w+_[^\s]+)\s+rdf:type\s+hist:(\w+)\s*\.'
        for match in re.finditer(type_pattern, chunk):
            uri = match.group(1)
            entity_type = match.group(2)
            uri_to_type[uri] = entity_type
        
        # 라벨 추출
        label_pattern = r'(hist:\w+_[^\s]+)\s+rdfs:label\s+"([^"]+)"\s*\.'
        for match in re.finditer(label_pattern, chunk):
            uri = match.group(1)
            label = match.group(2)
            label_to_uri[label] = uri
            
            # 라벨 변형 추가
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri
            
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri
        
        return {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 검사"""
        if self._cache is None or self._cache_mtime is None:
            return False
        
        current_mtime = os.path.getmtime(self.ttl_path)
        return self._cache_mtime == current_mtime


class BatchSPARQLExecutor:
    """배치 SPARQL 실행기 - LangGraph용"""
    
    def __init__(self, fuseki_url: str, config: PerformanceConfig = None):
        self.fuseki_url = fuseki_url
        self.config = config or PerformanceConfig()
    
    def process_entities_batch(self, entities: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """
        여러 엔티티에 대한 SPARQL 쿼리를 배치로 실행 (동기 버전)
        
        Args:
            entities: 엔티티 리스트
            keywords: 키워드 리스트
            
        Returns:
            업데이트된 엔티티 리스트
        """
        # 배치로 분할
        batches = [entities[i:i + self.config.sparql_batch_size] 
                  for i in range(0, len(entities), self.config.sparql_batch_size)]
        
        updated_entities = []
        
        # 각 배치를 병렬 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            for batch in batches:
                future = executor.submit(self._process_batch_sync, batch, keywords)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_result = future.result()
                    updated_entities.extend(batch_result)
                except Exception as e:
                    print(f"[ERROR] 배치 처리 에러: {e}")
        
        return updated_entities
    
    def _process_batch_sync(self, batch: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """단일 배치 동기 처리"""
        import requests
        
        updated_batch = []
        
        for entity in batch:
            uri = entity.get("uri")
            if not uri:
                entity.update({
                    "sparql_connections": 0,
                    "matched_connections": 0,
                    "has_keyword_in_connections": False,
                    "sparql_executed": False
                })
                updated_batch.append(entity)
                continue
            
            # URI 형식 변환
            full_uri = uri.replace("hist:", "http://www.example.org/korean-history#")
            
            sparql_query = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT DISTINCT ?connectedLabel WHERE {{
                    {{
                        <{full_uri}> ?p ?connected .
                        ?connected rdfs:label ?connectedLabel .
                        FILTER(?p != rdf:type)
                        FILTER(?p != rdfs:label)
                    }}
                    UNION
                    {{
                        ?connected ?p <{full_uri}> .
                        ?connected rdfs:label ?connectedLabel .
                        FILTER(?p != rdf:type)
                        FILTER(?p != rdfs:label)
                    }}
                }} LIMIT 50
            """
            
            try:
                response = requests.post(
                    f"{self.fuseki_url}/sparql",
                    data={"query": sparql_query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=self.config.sparql_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    bindings = data.get("results", {}).get("bindings", [])
                    connection_count = len(bindings)
                    
                    # 키워드 매칭 확인
                    matched_connections = []
                    for binding in bindings:
                        connected_label = binding.get("connectedLabel", {}).get("value", "")
                        if connected_label:
                            for kw in keywords:
                                if kw.lower() in connected_label.lower():
                                    matched_connections.append(connected_label)
                                    break
                    
                    entity.update({
                        "sparql_connections": connection_count,
                        "matched_connections": len(matched_connections),
                        "has_keyword_in_connections": len(matched_connections) > 0,
                        "sparql_executed": True
                    })
                    
                    # 간소화된 로그 (연결이 있을 때만)
                    if connection_count > 0:
                        print(f"    ✓ {entity.get('name', 'Unknown')}: {connection_count}개 연결 (매칭: {len(matched_connections)})")
                
                else:
                    entity.update({
                        "sparql_connections": 0,
                        "matched_connections": 0,
                        "has_keyword_in_connections": False,
                        "sparql_executed": False
                    })
            
            except Exception as e:
                entity.update({
                    "sparql_connections": 0,
                    "matched_connections": 0,
                    "has_keyword_in_connections": False,
                    "sparql_executed": False
                })
            
            updated_batch.append(entity)
        
        return updated_batch


class LazyVectorService:
    """지연 로딩 벡터 서비스 - LangGraph용"""
    
    def __init__(self, config: PerformanceConfig = None):
        self.config = config or PerformanceConfig()
        self._service = None
        self._initialized = False
    
    def search(self, query: str, top_k: int = 30, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        벡터 검색 (지연 로딩)
        
        Args:
            query: 검색 쿼리
            top_k: 상위 K개 결과
            threshold: 유사도 임계값
            
        Returns:
            검색 결과 리스트
        """
        if not self.config.lazy_load_vectors:
            return []
        
        if not self._initialized:
            self._initialize_service()
        
        if self._service is None:
            return []
        
        try:
            # TitleVectorService의 실제 인터페이스에 맞춰 호출
            if hasattr(self._service, 'search'):
                return self._service.search(query=query, top_k=top_k, threshold=threshold)
            else:
                print(f"[WARN] 벡터 서비스에 search 메서드가 없습니다")
                return []
        except Exception as e:
            print(f"[ERROR] 벡터 검색 실패: {e}")
            return []
    
    @property
    def conn(self):
        """TitleVectorService 호환성을 위한 conn 속성"""
        if not self._initialized:
            self._initialize_service()
        
        if self._service and hasattr(self._service, 'conn'):
            return self._service.conn
        return None
    
    def connect(self) -> bool:
        """연결 메서드 (TitleVectorService 호환성)"""
        if not self._initialized:
            self._initialize_service()
        
        if self._service and hasattr(self._service, 'connect'):
            return self._service.connect()
        
        return self._service is not None
    
    def _initialize_service(self):
        """벡터 서비스 초기화"""
        try:
            # 실제 TitleVectorService 사용
            from backend.db_pipeline.postgres.services.title_vector_service import TitleVectorService
            self._service = TitleVectorService()
            print("  ├─ [INFO] 실제 벡터 서비스 초기화 완료")
        except ImportError:
            print("[WARN] TitleVectorService import 실패")
            self._service = None
        except Exception as e:
            print(f"[ERROR] 벡터 서비스 초기화 실패: {e}")
            self._service = None
        finally:
            self._initialized = True


# 전역 성능 설정
DEFAULT_PERFORMANCE_CONFIG = PerformanceConfig(
    max_workers=4,
    sparql_batch_size=10,
    sparql_timeout=3,
    enable_ttl_cache=True,
    lazy_load_vectors=True
)