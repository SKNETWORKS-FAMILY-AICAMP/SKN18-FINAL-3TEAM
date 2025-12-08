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
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# CSV 필드 크기 제한 증가 (기본값 131072 바이트를 초과하는 필드 처리)
csv.field_size_limit(sys.maxsize)


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

        # LLM 초기화 (타임아웃 설정)
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0,
            timeout=120  # 60초 타임아웃 (LLM 호출이 너무 오래 걸리면 중단)
        )

        # URI 카운터 (중복 방지)
        self.uri_counter = {}

    def generate_uri(self, entity_type: str, name: str) -> str:
        """
        엔티티 URI 생성 (타입 포함으로 동명이인 구분)

        Args:
            entity_type: Person, Event, Place, Nation, Battle
            name: 엔티티 이름 (문자열 또는 정수)

        Returns:
            hist:Person_이순신, hist:Nation_중국 등
        """
        # 정수인 경우 문자열로 변환
        if isinstance(name, int):
            name = str(name)
        elif not isinstance(name, str):
            name = str(name)
        
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
        contents = row['contents'][:700]

        # 5가지 추론 + 이전 데이터 분석 결과 기반 최적화 프롬프트
        prompt = f"""조선시대 역사 데이터에서 **명시적 관계**만 추출하세요.

[입력]
카테고리: {category} | 제목: {title}
요약: {summary}
내용: {contents}

[허용된 타입] Person, Event, Battle, Place, Nation, Policy, Institution, Document

[허용된 속성 - 이것만 사용]
Person: hasRank(관직), hasBirthYear, hasDeathYear, hasAchievement, hasField(학문분야)
Event/Battle: hasYear, hasStartYear, hasEndYear
Institution: hasYear, hasPurpose, hasFunction
Document: hasYear
Place: hasYear, hasLocation

[허용된 관계 - 명시적으로 언급된 경우만]
- Person→Event: participatesIn, commands (전투 지휘)
- Person→Person: teacherOf, studentOf, servedUnder (군주), contemporaryWith
- Person→Nation: affiliatedWith
- Person→Institution: affiliatedWith, founded, reformed
- Person→Document: authored, compiled
- Event→Event: leadsTo, causes, partOf
- Institution→Person: establishedBy
- Policy→Person: initiatedBy
- hasMotive: Person의 행동 동기 (학문추구/개혁/충절/방어/민생안정)

[카테고리별 JSON 예시]

인물 예시:
{{
  "main_entity": {{"type": "Person", "name": "강거효", "properties": {{"hasRank": "병조정랑", "hasAchievement": "학문과 절의로 명성"}}}},
  "related_entities": [{{"type": "Institution", "name": "사헌부"}}, {{"type": "Event", "name": "무오사화"}}],
  "relations": [
    {{"subject": "강거효", "predicate": "affiliatedWith", "object": "사헌부"}},
    {{"subject": "강거효", "predicate": "participatesIn", "object": "무오사화"}}
  ]
}}

제도 예시:
{{
  "main_entity": {{"type": "Institution", "name": "선공감", "properties": {{"hasYear": 1392, "hasFunction": "토목공사 감독"}}}},
  "related_entities": [{{"type": "Nation", "name": "조선"}}],
  "relations": [{{"subject": "선공감", "predicate": "affiliatedWith", "object": "조선"}}]
}}

문헌 예시:
{{
  "main_entity": {{"type": "Document", "name": "목민심서", "properties": {{"hasYear": 1818}}}},
  "related_entities": [{{"type": "Person", "name": "정약용"}}],
  "relations": [{{"subject": "정약용", "predicate": "authored", "object": "목민심서"}}]
}}

[금지 규칙]
❌ 단순 언급만으로 관계 생성 금지 (내용에 "정종이 언급됨" → 관계 생성 X)
❌ Person→Place 직접 관계 금지 (leadsTo, influences, causes)
❌ Event→Place 직접 관계 금지 (방향 오류)
❌ Person resultsIn Person 금지 (출산 관계 추출 X)
❌ 허용되지 않은 속성 생성 금지 (hasClan, hasFather, hasCourtesyName 등)

[출력 규칙]
JSON 구조:
{{
  "main_entity": {{"type": "...", "name": "...", "properties": {{...}}}}  // 1개 (필수)
  "related_entities": [{{...}}, {{...}}]  // 최대 4개 (배열)
  "relations": [{{...}}, {{...}}]  // 최대 6개 (배열)
}}

- main_entity: 1개 (필수, properties 개수 제한 없음)
- related_entities: 최대 4개 (명시적 관계가 있는 엔티티만)
- relations: 최대 6개 (허용된 predicate만 사용)
- properties: 개수 제한 없음 (허용된 속성만 사용, 내용에 있는 만큼 추출)
- 반드시 유효한 JSON만 출력
"""

        try:
            # LLM 호출 (타임아웃 60초)
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

        # name이 정수인 경우 문자열로 변환
        if isinstance(name, int):
            name = str(name)
        elif not isinstance(name, str):
            name = str(name) if name else ""

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

        # subject가 정수인 경우 문자열로 변환
        if isinstance(subject, int):
            subject = str(subject)
        elif not isinstance(subject, str):
            subject = str(subject)
        
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

    def process_extraction_result(self, extraction_result: Dict[str, Any]) -> List[str]:
        """
        추출 결과를 TTL 트리플로 변환

        Args:
            extraction_result: LLM 추출 결과

        Returns:
            TTL 트리플 리스트
        """
        # 엔티티 → TTL 변환
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

        # 관계 → TTL 변환
        for relation in extraction_result.get("relations", []):
            triple = self.relation_to_ttl(relation, entity_uris)
            if triple:
                all_triples.append(triple)

        return all_triples

    def process_csv_row(self, row: Dict[str, str]) -> List[str]:
        """
        CSV 행을 처리하여 TTL 트리플 생성 (단일 항목 처리)

        Args:
            row: CSV 행

        Returns:
            TTL 트리플 리스트
        """
        # 1. LLM으로 엔티티 및 관계 추출
        extraction_result = self.extract_entities_and_relations(row)

        # 2. 추출 결과 → TTL 변환
        return self.process_extraction_result(extraction_result)

    def generate_ttl_file(self, limit: int = None, resume: bool = True, batch_size: int = 50):
        """
        CSV 전체를 읽어서 TTL 파일 생성 (체크포인트 기능 포함)

        Args:
            limit: 처리할 행 수 제한 (None이면 전체)
            resume: True면 이전 진행 상황에서 재개
            batch_size: 몇 개마다 저장할지 (기본 50개)
        """
        print(f"📖 CSV 읽기: {self.csv_path}")

        # ttl_2로 저장 (기존 파일 보존)
        output_path = os.path.join(self.output_dir, "korean_history_instances_2.ttl")
        checkpoint_path = os.path.join(self.output_dir, ".checkpoint")
        error_log_path = os.path.join(self.output_dir, "error_log.txt")

        # 체크포인트에서 시작 위치 읽기
        start_index = 0
        if resume and os.path.exists(checkpoint_path):
            with open(checkpoint_path, 'r') as f:
                start_index = int(f.read().strip())
            print(f"🔄 체크포인트에서 재개: {start_index}번째부터")

        # 첫 시작인 경우 기존 파일 백업 (ttl_2 파일이 있는 경우)
        if start_index == 0 and os.path.exists(output_path):
            backup_path = output_path + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(output_path, backup_path)
            print(f"📦 기존 파일 백업: {os.path.basename(backup_path)}")

        # TTL 헤더 작성 (파일이 없거나 첫 시작인 경우)
        if not os.path.exists(output_path) or start_index == 0:
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
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(header))
            if start_index > 0:
                print(f"📝 TTL 파일 생성: {os.path.basename(output_path)} (체크포인트에서 재개)")

        # 배치 저장용 버퍼
        batch_triples = []
        processed_count = 0
        error_count = 0
        current_index = start_index  # 현재 처리 중인 행 인덱스 추적

        def save_batch_and_checkpoint(index: int):
            """배치 저장 및 체크포인트 업데이트"""
            nonlocal batch_triples
            if batch_triples:
                try:
                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write("\n".join(batch_triples))
                    batch_triples = []
                    
                    # 체크포인트 저장
                    with open(checkpoint_path, 'w') as f:
                        f.write(str(index))
                    print(f"    💾 저장 완료 ({index}개 처리됨, 체크포인트 업데이트)")
                    return True
                except Exception as e:
                    print(f"    ⚠️ 저장 중 오류: {e}")
                    return False
            return False

        try:
            # CSV 읽기 (BOM 처리)
            with open(self.csv_path, 'r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)

                for i, row in enumerate(reader):
                    # 시작 위치 이전은 건너뛰기
                    if i < start_index:
                        continue

                    if limit and i >= limit:
                        break

                    current_index = i + 1  # 현재 처리 중인 행 번호 (1-based)
                    print(f"  처리 중: {current_index}. {row['title']}")

                    try:
                        # 트리플 생성
                        triples = self.process_csv_row(row)

                        # 배치에 추가
                        if triples:
                            batch_triples.append(f"\n# {row['title']} ({row['category']})")
                            batch_triples.extend(triples)
                            batch_triples.append("")

                        processed_count += 1

                    except Exception as e:
                        error_count += 1
                        print(f"    ❌ 에러: {e}")
                        # 에러 로그 기록
                        try:
                            with open(error_log_path, 'a', encoding='utf-8') as f:
                                f.write(f"{current_index}. {row['title']}: {e}\n")
                        except:
                            pass
                        # 오류 발생 시에도 저장 (데이터 손실 방지)
                        if batch_triples:
                            save_batch_and_checkpoint(current_index)

                    # 배치 저장 (batch_size마다)
                    if processed_count > 0 and processed_count % batch_size == 0:
                        save_batch_and_checkpoint(current_index)

        except KeyboardInterrupt:
            print("\n⚠️ 사용자에 의해 중단됨 (Ctrl+C)")
            # 진행된 내용 저장
            if batch_triples:
                save_batch_and_checkpoint(current_index)
            print(f"💾 중단 전까지의 진행 상황이 저장되었습니다 (체크포인트: {current_index})")
            raise
        except Exception as e:
            print(f"\n❌ 치명적 오류 발생: {e}")
            # 진행된 내용 저장
            if batch_triples:
                save_batch_and_checkpoint(current_index)
            print(f"💾 오류 발생 전까지의 진행 상황이 저장되었습니다 (체크포인트: {current_index})")
            raise
        finally:
            # 남은 배치 저장 (정상 종료 또는 오류 발생 시)
            if batch_triples:
                save_batch_and_checkpoint(current_index)

        # 체크포인트 삭제 (완료 시에만)
        if os.path.exists(checkpoint_path):
            # 모든 행을 처리했는지 확인
            try:
                # CSV 필드 크기 제한 증가
                csv.field_size_limit(sys.maxsize)
                with open(self.csv_path, 'r', encoding='utf-8-sig') as csv_file:
                    reader = csv.DictReader(csv_file)
                    total_rows = sum(1 for _ in reader)
                
                # current_index는 1-based이므로, total_rows와 비교할 때 주의
                # enumerate는 0부터 시작하므로 마지막 행의 인덱스는 total_rows-1
                # current_index = i + 1이므로, 마지막 행 처리 시 current_index = total_rows
                if current_index > total_rows:
                    os.remove(checkpoint_path)
                    print(f"\n✅ TTL 생성 완료: {output_path}")
                else:
                    print(f"\n⚠️ 부분 완료: {output_path}")
                    print(f"   진행률: {current_index}/{total_rows} ({current_index*100//total_rows if total_rows > 0 else 0}%)")
            except Exception as e:
                print(f"\n⚠️ 완료 확인 실패: {e}")
                pass

        print(f"   총 처리: {processed_count}개")
        print(f"   에러: {error_count}개")
        if error_count > 0:
            print(f"   에러 로그: {error_log_path}")


def main():
    """메인 함수"""
    import sys

    # 경로 설정 (상대 경로 사용)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    output_dir = script_dir.parent / "instances"

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    # 생성기 초기화
    generator = LLMTTLGenerator(csv_path, output_dir)

    # 명령줄 인자 처리
    # --all: 전체 처리
    # --limit N: N개만 처리 (기본: 10)
    # --no-resume: 처음부터 시작
    limit = 10
    resume = True

    if "--all" in sys.argv:
        limit = None
        print("🚀 전체 데이터 TTL 생성 시작...")
    else:
        for i, arg in enumerate(sys.argv):
            if arg == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
        print(f"🚀 TTL 생성 시작 (limit={limit})...")

    if "--no-resume" in sys.argv:
        resume = False
        print("   (처음부터 시작)")

    generator.generate_ttl_file(limit=limit, resume=resume)


if __name__ == "__main__":
    main()
