"""
LLM 기반 TTL 생성기

CSV 데이터를 읽어서 LLM을 사용하여 온톨로지 트리플(TTL)로 변환

처리 과정:
1. CSV 읽기 (category, title, summary, contents)
2. LLM으로 엔티티 추출 및 관계 파악
3. TTL 트리플 생성
4. 파일 저장
"""

import os
import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class LLMTTLGenerator:
    """LLM 기반 TTL 생성기"""

    def __init__(self, csv_path: str, output_dir: str):
        """
        Args:
            csv_path: CSV 파일 경로
            output_dir: TTL 출력 디렉토리
        """
        self.csv_path = csv_path
        self.output_dir = output_dir

        # LLM 초기화
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            temperature=0
        )

        # URI 카운터 (중복 방지)
        self.uri_counter = {}

    def generate_uri(self, entity_type: str, name: str) -> str:
        """
        엔티티 URI 생성 (타입 포함으로 동명이인 구분)

        Args:
            entity_type: Person, Event, Place, Nation, Battle
            name: 엔티티 이름

        Returns:
            hist:Person_이순신, hist:Nation_중국 등
        """
        # 공백 제거
        clean_name = name.replace(" ", "").replace("-", "")

        # 타입_이름 형식으로 URI 생성 (타입별로 구분)
        return f"hist:{entity_type}_{clean_name}"

    def extract_entities_and_relations(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        LLM을 사용하여 CSV 행에서 엔티티 및 관계 추출

        Args:
            row: CSV 행 (category, title, summary, contents)

        Returns:
            {
                "main_entity": {...},
                "related_entities": [...],
                "relations": [...]
            }
        """

        category = row['category']
        title = row['title']
        summary = row['summary']
        contents = row['contents'][:1000]  # 처음 1000자만

        prompt = f"""당신은 조선시대 역사 데이터를 온톨로지 트리플로 변환하는 전문가입니다.

아래 데이터에서 **엔티티**와 **관계**를 추출하세요.

**입력 데이터:**
- 카테고리: {category}
- 제목: {title}
- 요약: {summary}
- 내용: {contents}

**출력 형식 (JSON):**
{{
  "main_entity": {{
    "type": "Person|Event|Battle|Place|Nation|Policy|Institution",
    "name": "이순신",
    "properties": {{
      "hasAlias": ["충무공"],
      "hasBirthYear": 1545,
      "hasDeathYear": 1598,
      "hasRank": ["삼도수군통제사"],
      "hasAchievement": "임진왜란 수군 지휘"
    }}
  }},
  "related_entities": [
    {{"type": "Event", "name": "임진왜란"}},
    {{"type": "Battle", "name": "명량해전"}},
    {{"type": "Place", "name": "한산도"}},
    {{"type": "Nation", "name": "조선"}},
    {{"type": "Policy", "name": "쇄국정책"}},
    {{"type": "Institution", "name": "집현전"}}
  ],
  "relations": [
    {{"subject": "이순신", "predicate": "participatesIn", "object": "임진왜란"}},
    {{"subject": "이순신", "predicate": "commands", "object": "명량해전"}},
    {{"subject": "명량해전", "predicate": "partOf", "object": "임진왜란"}},
    {{"subject": "명량해전", "predicate": "hasYear", "object": 1597}},
    {{"subject": "이순신", "predicate": "affiliatedWith", "object": "조선"}},
    {{"subject": "쇄국정책", "predicate": "initiatedBy", "object": "흥선대원군"}},
    {{"subject": "집현전", "predicate": "establishedBy", "object": "세종대왕"}}
  ]
}}

**주의사항:**
- main_entity는 제목(title)에 해당하는 핵심 엔티티
- related_entities는 내용에 언급된 다른 엔티티들
- relations는 엔티티 간 관계 (participatesIn, commands, leadsTo, occursAt, hasYear 등)
- 반드시 유효한 JSON만 출력
"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result

        except Exception as e:
            print(f"⚠️ LLM 추출 실패 ({title}): {e}")
            return {
                "main_entity": {"type": category, "name": title, "properties": {}},
                "related_entities": [],
                "relations": []
            }

    def entity_to_ttl(self, entity: Dict[str, Any]) -> List[str]:
        """
        엔티티를 TTL 트리플로 변환

        Args:
            entity: {"type": "Person", "name": "이순신", "properties": {...}}

        Returns:
            ["hist:YiSunSin rdf:type hist:Person .", ...]
        """
        triples = []

        entity_type = entity.get("type", "")
        name = entity.get("name", "")
        properties = entity.get("properties", {})

        if not entity_type or not name:
            return []

        # URI 생성
        uri = self.generate_uri(entity_type, name)

        # rdf:type 트리플
        triples.append(f"{uri} rdf:type hist:{entity_type} .")

        # rdfs:label (언어 태그 제거)
        triples.append(f'{uri} rdfs:label "{name}" .')

        # 속성 트리플 (언어 태그 제거)
        for prop, value in properties.items():
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, str):
                        triples.append(f'{uri} hist:{prop} "{v}" .')
                    else:
                        triples.append(f'{uri} hist:{prop} {v} .')
            elif isinstance(value, str):
                triples.append(f'{uri} hist:{prop} "{value}" .')
            elif isinstance(value, int):
                triples.append(f'{uri} hist:{prop} {value} .')

        return triples

    def relation_to_ttl(self, relation: Dict[str, Any], entity_uris: Dict[str, str]) -> str:
        """
        관계를 TTL 트리플로 변환

        Args:
            relation: {"subject": "이순신", "predicate": "participatesIn", "object": "임진왜란"}
            entity_uris: {"이순신": "hist:YiSunSin", ...}

        Returns:
            "hist:YiSunSin hist:participatesIn hist:ImjinWar ."
        """
        subject = relation.get("subject", "")
        predicate = relation.get("predicate", "")
        obj = relation.get("object")

        subject_uri = entity_uris.get(subject, f"hist:{subject.replace(' ', '')}")

        # object가 숫자인 경우 (연도 등)
        if isinstance(obj, int):
            return f"{subject_uri} hist:{predicate} {obj} ."
        # object가 엔티티인 경우
        elif isinstance(obj, str) and obj in entity_uris:
            object_uri = entity_uris[obj]
            return f"{subject_uri} hist:{predicate} {object_uri} ."
        # object가 문자열인 경우 (언어 태그 제거)
        elif isinstance(obj, str):
            return f'{subject_uri} hist:{predicate} "{obj}" .'

        return ""

    def process_csv_row(self, row: Dict[str, str]) -> List[str]:
        """
        CSV 행을 처리하여 TTL 트리플 생성

        Args:
            row: CSV 행

        Returns:
            TTL 트리플 리스트
        """
        # 1. LLM으로 엔티티 및 관계 추출
        extraction_result = self.extract_entities_and_relations(row)

        # 2. 엔티티 → TTL 변환
        all_triples = []
        entity_uris = {}

        # Main entity
        main_entity = extraction_result.get("main_entity", {})
        if main_entity:
            main_name = main_entity.get("name", "")
            main_type = main_entity.get("type", "")
            if main_name and main_type:
                entity_uris[main_name] = self.generate_uri(main_type, main_name)
                all_triples.extend(self.entity_to_ttl(main_entity))

        # Related entities
        for entity in extraction_result.get("related_entities", []):
            name = entity.get("name", "")
            etype = entity.get("type", "")
            if name and etype:
                entity_uris[name] = self.generate_uri(etype, name)
                all_triples.extend(self.entity_to_ttl(entity))

        # 3. 관계 → TTL 변환
        for relation in extraction_result.get("relations", []):
            triple = self.relation_to_ttl(relation, entity_uris)
            if triple:
                all_triples.append(triple)

        return all_triples

    def generate_ttl_file(self, limit: int = None):
        """
        CSV 전체를 읽어서 TTL 파일 생성 (메모리 기반 방식)

        Args:
            limit: 처리할 행 수 제한 (None이면 전체)
        """
        print(f"📖 CSV 읽기: {self.csv_path}")

        output_path = os.path.join(self.output_dir, "korean_history_instances.ttl")

        # TTL 헤더
        header = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix hist: <http://www.example.org/korean-history#> .",
            "",
            "# 조선시대 역사 인스턴스 데이터",
            ""
        ]

        # 메모리에 모든 트리플 저장
        all_triples = ["\n".join(header)]

        # CSV 읽기 (BOM 처리)
        with open(self.csv_path, 'r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)

            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break

                print(f"  처리 중: {i+1}. {row['title']}")

                # 트리플 생성
                triples = self.process_csv_row(row)

                # 메모리에 추가
                if triples:
                    all_triples.append(f"# {row['title']} ({row['category']})")
                    all_triples.extend(triples)
                    all_triples.append("")  # 빈 줄

        # 한 번에 파일 저장
        print(f"\n💾 파일 저장 중...")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_triples))

        print(f"\n✅ TTL 생성 완료: {output_path}")
        print(f"   총 데이터 항목: {i+1}개")
        print(f"   총 라인 수: {len(all_triples)}")


def main():
    """메인 함수"""

    # 경로 설정 (상대 경로 사용)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    output_dir = script_dir.parent / "instances"

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    # 생성기 초기화
    generator = LLMTTLGenerator(csv_path, output_dir)

    # TTL 생성 (처음 10개만 테스트)
    print("🚀 TTL 생성 시작...")
    generator.generate_ttl_file(limit=10)


if __name__ == "__main__":
    main()
