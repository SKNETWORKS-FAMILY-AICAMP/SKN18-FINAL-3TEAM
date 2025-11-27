"""
Entity Extractor Node - Milvus pgvector 기반

질문에서 핵심 엔티티 추출 및 URI 매핑:
- Milvus 벡터 검색으로 엔티티 식별
- 온톨로지 URI 매핑 (자연어 → hist:URI)
- 유사 엔티티 검색 (동명이인, 별칭)
- 온톨로지 스키마 검색 (클래스, 속성)

3가지 Milvus 작업:
1. Entity Linking: "이순신" → hist:YiSunSin
2. Similar Entity Search: "이순신"과 유사한 인물 찾기
3. Schema Search: Person, Event 등 온톨로지 클래스 검색
"""

import os
from typing import List, Dict, Any
from langgraph_structure.state import GraphState
from langchain_openai import OpenAIEmbeddings

# TODO: Milvus 연결은 추후 구현
# from pymilvus import Collection, connections


class MilvusEntityExtractor:
    """Milvus 기반 엔티티 추출기 (설계)"""

    def __init__(self):
        # Milvus 설정 (연결은 추후)
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = os.getenv("MILVUS_PORT", "19530")

        # 컬렉션 이름
        self.entity_collection = "historical_entities"  # 인물, 사건, 장소 등
        self.schema_collection = "ontology_schema"      # 클래스, 속성

        # Embedding 모델
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        )

        # TODO: Milvus 연결 (추후 구현)
        # connections.connect(host=self.milvus_host, port=self.milvus_port)
        # self.entity_coll = Collection(self.entity_collection)
        # self.schema_coll = Collection(self.schema_collection)

    def extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        메인 엔티티 추출 함수

        Args:
            query: 사용자 질문

        Returns:
            List[Dict]: 추출된 엔티티 목록
            [
                {
                    "name": "이순신",
                    "type": "Person",
                    "uri": "hist:YiSunSin",
                    "similarity": 0.98,
                    "aliases": ["충무공", "李舜臣"],
                    "description": "조선 수군 통제사"
                },
                ...
            ]
        """

        # 1. 질문 임베딩
        query_vector = self.embeddings.embed_query(query)

        # 2. Milvus 벡터 검색 (Entity Linking)
        entities = self._search_entities(query_vector, top_k=10)

        # 3. 유사 엔티티 확장 (Similar Entity Search)
        enriched_entities = self._enrich_with_similar_entities(entities, top_k=5)

        # 4. 엔티티 타입 필터링 및 정제
        filtered_entities = self._filter_and_rank_entities(enriched_entities)

        return filtered_entities

    def _search_entities(self, query_vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Milvus에서 엔티티 검색 (Entity Linking)

        Args:
            query_vector: 질문 임베딩 벡터
            top_k: 상위 K개 결과

        Returns:
            List[Dict]: 검색된 엔티티 목록
        """

        # TODO: 실제 Milvus 검색 (추후 구현)
        # search_params = {
        #     "metric_type": "COSINE",
        #     "params": {"nprobe": 10}
        # }
        #
        # results = self.entity_coll.search(
        #     data=[query_vector],
        #     anns_field="embedding",
        #     param=search_params,
        #     limit=top_k,
        #     output_fields=["entity_name", "entity_type", "uri", "aliases", "description"]
        # )
        #
        # entities = []
        # for hits in results:
        #     for hit in hits:
        #         entities.append({
        #             "name": hit.entity.get("entity_name"),
        #             "type": hit.entity.get("entity_type"),
        #             "uri": hit.entity.get("uri"),
        #             "similarity": hit.score,
        #             "aliases": hit.entity.get("aliases", []),
        #             "description": hit.entity.get("description", "")
        #         })

        # 임시 Mock 데이터 (설계 단계)
        print(f"   🔍 Milvus Entity Linking: 질문 임베딩 검색 중... (Top {top_k})")

        entities = [
            {
                "name": "이순신",
                "type": "Person",
                "uri": "hist:YiSunSin",
                "similarity": 0.98,
                "aliases": ["충무공", "李舜臣"],
                "description": "조선 수군 통제사"
            },
            {
                "name": "임진왜란",
                "type": "Event",
                "uri": "hist:ImjinWar",
                "similarity": 0.95,
                "aliases": ["壬辰倭亂", "정유재란"],
                "description": "1592-1598년 일본의 조선 침략"
            }
        ]

        return entities

    def _enrich_with_similar_entities(
        self,
        entities: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        유사 엔티티로 확장 (Similar Entity Search)

        Args:
            entities: 기존 엔티티 목록
            top_k: 각 엔티티당 유사 엔티티 K개

        Returns:
            List[Dict]: 유사 엔티티가 추가된 엔티티 목록
        """

        enriched = []

        for entity in entities:
            # 엔티티 임베딩 (URI 기반)
            entity_vector = self.embeddings.embed_query(entity["name"])

            # TODO: 유사 엔티티 검색 (추후 구현)
            # similar_results = self.entity_coll.search(
            #     data=[entity_vector],
            #     anns_field="embedding",
            #     param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            #     limit=top_k,
            #     expr=f"entity_type == '{entity['type']}' and uri != '{entity['uri']}'",
            #     output_fields=["entity_name", "uri", "description"]
            # )
            #
            # similar_entities = []
            # for hits in similar_results:
            #     for hit in hits:
            #         similar_entities.append({
            #             "name": hit.entity.get("entity_name"),
            #             "uri": hit.entity.get("uri"),
            #             "similarity": hit.score,
            #             "description": hit.entity.get("description", "")
            #         })

            # 임시 Mock 데이터
            print(f"      ↳ 유사 엔티티 검색: {entity['name']} ({entity['type']})")

            similar_entities = []
            if entity["type"] == "Person":
                similar_entities = [
                    {"name": "원균", "uri": "hist:WonGyun", "similarity": 0.82, "description": "조선 수군 장수"},
                    {"name": "권율", "uri": "hist:GwonYul", "similarity": 0.78, "description": "조선 육군 장수"}
                ]
            elif entity["type"] == "Event":
                similar_entities = [
                    {"name": "명량해전", "uri": "hist:BattleOfMyeongnyang", "similarity": 0.88, "description": "1597년 명량 해협 전투"},
                    {"name": "한산도대첩", "uri": "hist:BattleOfHansando", "similarity": 0.85, "description": "1592년 한산도 해전"}
                ]

            # 엔티티에 유사 엔티티 추가
            entity["similar_entities"] = similar_entities
            enriched.append(entity)

        return enriched

    def _filter_and_rank_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        엔티티 필터링 및 순위 정렬

        Args:
            entities: 엔티티 목록

        Returns:
            List[Dict]: 필터링 및 정렬된 엔티티 (상위 10개)
        """

        # 1. 유사도 임계값 필터링 (0.7 이상)
        filtered = [e for e in entities if e["similarity"] >= 0.7]

        # 2. 유사도 기준 정렬
        sorted_entities = sorted(filtered, key=lambda x: x["similarity"], reverse=True)

        # 3. 상위 10개 선택
        top_entities = sorted_entities[:10]

        return top_entities

    def search_ontology_schema(self, entity_types: List[str]) -> Dict[str, Any]:
        """
        온톨로지 스키마 검색 (Schema Search)

        MultiQueryGenerator에서 SPARQL 생성 시 사용할 클래스/속성 검색

        Args:
            entity_types: 검색할 엔티티 타입 리스트 ["Person", "Event", "Place"]

        Returns:
            Dict: 온톨로지 스키마 정보
            {
                "classes": ["hist:Person", "hist:Event", "hist:Place"],
                "properties": {
                    "Person": ["hist:participatesIn", "hist:hasRole", "hist:bornIn"],
                    "Event": ["hist:occursAt", "hist:hasDate", "hist:leadsTo"]
                }
            }
        """

        # TODO: Milvus 스키마 검색 (추후 구현)
        # schema_results = {}
        # for entity_type in entity_types:
        #     type_vector = self.embeddings.embed_query(f"{entity_type} ontology class")
        #
        #     results = self.schema_coll.search(
        #         data=[type_vector],
        #         anns_field="embedding",
        #         param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        #         limit=10,
        #         expr=f"schema_type == 'class' or schema_type == 'property'",
        #         output_fields=["class_name", "properties", "domain", "range"]
        #     )
        #
        #     schema_results[entity_type] = results

        # 임시 Mock 데이터
        print(f"   📐 Ontology Schema Search: {entity_types}")

        schema = {
            "classes": ["hist:Person", "hist:Event", "hist:Place", "hist:Nation"],
            "properties": {
                "Person": [
                    "hist:participatesIn",
                    "hist:hasRole",
                    "hist:bornIn",
                    "hist:diedIn",
                    "hist:commands"
                ],
                "Event": [
                    "hist:occursAt",
                    "hist:hasDate",
                    "hist:leadsTo",
                    "hist:causedBy",
                    "hist:involvesPerson",
                    "hist:hasParticipant"
                ],
                "Place": [
                    "hist:locatedIn",
                    "hist:isLocationOf"
                ],
                "Nation": [
                    "hist:engagesIn",
                    "hist:hasLeader"
                ]
            }
        }

        return schema


def entity_extractor_node(state: GraphState) -> GraphState:
    """
    Milvus 기반 엔티티 추출 노드

    처리 과정:
    1. 질문에서 핵심 엔티티 추출 (Milvus 벡터 검색)
    2. 온톨로지 URI 매핑 (Entity Linking)
    3. 유사 엔티티 확장 (Similar Entity Search)
    4. 온톨로지 스키마 검색 (MultiQueryGenerator용)

    Args:
        state: GraphState (query 포함)

    Returns:
        GraphState: extracted_entities, ontology_schema 추가
    """

    query = state.get("query", "")

    print(f"\n🔍 Entity Extraction (Milvus)")
    print(f"   질문: {query}")

    # Milvus 엔티티 추출기 초기화
    extractor = MilvusEntityExtractor()

    try:
        # 1. 엔티티 추출 및 URI 매핑
        entities = extractor.extract_entities(query)

        print(f"\n   ✅ 추출된 엔티티: {len(entities)}개")
        for i, entity in enumerate(entities[:5], 1):  # 상위 5개만 출력
            print(f"      {i}. [{entity['type']}] {entity['name']} → {entity['uri']} (유사도: {entity['similarity']:.2%})")

            # 유사 엔티티 출력
            if entity.get("similar_entities"):
                for similar in entity["similar_entities"][:2]:  # 상위 2개만
                    print(f"         ↳ {similar['name']} ({similar['similarity']:.2%})")

        # 2. 온톨로지 스키마 검색 (MultiQueryGenerator용)
        entity_types = list(set([e["type"] for e in entities]))
        ontology_schema = extractor.search_ontology_schema(entity_types)

        print(f"\n   📐 온톨로지 스키마:")
        print(f"      - 클래스: {', '.join(ontology_schema['classes'])}")
        for entity_type, props in ontology_schema["properties"].items():
            print(f"      - {entity_type}: {len(props)}개 속성")

    except Exception as e:
        print(f"   ⚠️ 엔티티 추출 실패: {e}")
        entities = []
        ontology_schema = {"classes": [], "properties": {}}

    return {
        **state,
        "extracted_entities": entities,
        "ontology_schema": ontology_schema,
        "executed_nodes": state.get("executed_nodes", []) + ["entity_extractor"]
    }
