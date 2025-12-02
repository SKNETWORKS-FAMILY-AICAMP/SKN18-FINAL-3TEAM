"""
Inference Triple Generator

Jena Reasoner 추론 결과를 TTL 형식의 Triple로 변환하여
Fuseki에 저장할 수 있는 형태로 생성
"""

from typing import Dict, List, Any
from datetime import datetime


class InferenceTripleGenerator:
    """추론 결과를 RDF Triple로 변환"""

    def __init__(self, namespace: str = "http://www.example.org/korean-history#"):
        """
        Args:
            namespace: 온톨로지 네임스페이스
        """
        self.namespace = namespace
        self.prefix_hist = f"@prefix hist: <{namespace}> ."
        self.prefix_rdf = "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ."
        self.prefix_rdfs = "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ."
        self.prefix_xsd = "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."

    def generate_ttl_from_inference_results(
        self,
        inference_results: Dict[str, Any],
        session_id: str = None
    ) -> str:
        """
        병렬 추론 결과를 TTL 형식으로 변환

        Args:
            inference_results: parallel_inference_executor_node의 결과
                {
                    "causal": {"bindings": [...], "status": "success"},
                    "person": {"bindings": [...], "status": "success"},
                    ...
                }
            session_id: 추론 세션 ID (없으면 타임스탬프 사용)

        Returns:
            TTL 형식의 문자열
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        ttl_lines = [
            "# 추론 결과 Triples",
            f"# Generated at: {datetime.now().isoformat()}",
            f"# Session ID: {session_id}",
            "",
            self.prefix_hist,
            self.prefix_rdf,
            self.prefix_rdfs,
            self.prefix_xsd,
            ""
        ]

        total_triples = 0

        # 각 Thread별 추론 결과 처리
        for thread_type, result in inference_results.items():
            if result.get("status") != "success":
                continue

            bindings = result.get("bindings", [])
            if not bindings:
                continue

            ttl_lines.append(f"# {thread_type.upper()} 추론 결과 ({len(bindings)}개)")
            ttl_lines.append("")

            # 각 바인딩을 Triple로 변환
            triples = self._convert_bindings_to_triples(thread_type, bindings)
            ttl_lines.extend(triples)
            ttl_lines.append("")

            total_triples += len(triples)

        ttl_lines.append(f"# 총 {total_triples}개 Triple 생성")

        return "\n".join(ttl_lines)

    def _convert_bindings_to_triples(self, thread_type: str, bindings: List[Dict]) -> List[str]:
        """
        SPARQL 바인딩을 TTL Triple로 변환

        Args:
            thread_type: 추론 타입 (causal, person, temporal, pattern, motive)
            bindings: SPARQL 결과 바인딩 리스트

        Returns:
            TTL 형식의 Triple 문자열 리스트
        """
        triples = []

        for binding in bindings:
            # 바인딩에서 주어, 술어, 객체 추출
            triple = self._extract_triple_from_binding(thread_type, binding)
            if triple:
                triples.append(triple)

        return triples

    def _extract_triple_from_binding(self, thread_type: str, binding: Dict) -> str:
        """
        개별 바인딩에서 Triple 추출

        Args:
            thread_type: 추론 타입
            binding: SPARQL 결과 바인딩
                {
                    "subject": {"type": "uri", "value": "http://...#Person1"},
                    "predicate": {"type": "uri", "value": "http://...#hasRelationshipWith"},
                    "object": {"type": "uri", "value": "http://...#Person2"}
                }

        Returns:
            TTL 형식의 Triple 문자열
        """
        # 일반적인 패턴: subject, predicate, object
        subject = binding.get("subject") or binding.get("s")
        predicate = binding.get("predicate") or binding.get("p")
        obj = binding.get("object") or binding.get("o")

        # Thread별 특수 패턴 처리
        if thread_type == "causal":
            subject = subject or binding.get("cause")
            obj = obj or binding.get("effect")
            if not predicate:
                predicate = {"type": "uri", "value": f"{self.namespace}leadsTo"}

        elif thread_type == "person":
            subject = subject or binding.get("person")
            obj = obj or binding.get("event") or binding.get("person2")

        elif thread_type == "temporal":
            subject = subject or binding.get("event1") or binding.get("person1")
            obj = obj or binding.get("event2") or binding.get("person2")

        elif thread_type == "pattern":
            subject = subject or binding.get("e1") or binding.get("person")
            obj = obj or binding.get("e2") or binding.get("pattern")

        elif thread_type == "motive":
            subject = subject or binding.get("person")
            obj = obj or binding.get("motive")
            if not predicate:
                predicate = {"type": "uri", "value": f"{self.namespace}hasMotive"}

        elif thread_type == "policy":
            subject = subject or binding.get("policy")
            obj = obj or binding.get("event") or binding.get("person") or binding.get("impact")
            if not predicate:
                # 기본 술어 (policy → event)
                predicate = {"type": "uri", "value": f"{self.namespace}leadsTo"}

        elif thread_type == "institution":
            subject = subject or binding.get("institution")
            obj = obj or binding.get("policy") or binding.get("person")
            if not predicate:
                # 기본 술어 (institution → policy)
                predicate = {"type": "uri", "value": f"{self.namespace}relatedToPolicy"}

        if not all([subject, predicate, obj]):
            return ""

        # URI/리터럴 포맷팅
        s = self._format_value(subject)
        p = self._format_value(predicate)
        o = self._format_value(obj)

        if s and p and o:
            return f"{s} {p} {o} ."

        return ""

    def _format_value(self, value_dict: Dict) -> str:
        """
        SPARQL 값을 TTL 형식으로 변환

        Args:
            value_dict: {"type": "uri"|"literal", "value": "...", "datatype": "..."}

        Returns:
            TTL 형식의 값
        """
        if not value_dict or "value" not in value_dict:
            return ""

        value = value_dict["value"]
        value_type = value_dict.get("type", "literal")

        if value_type == "uri":
            # URI를 짧은 형태로 변환
            if value.startswith(self.namespace):
                short_name = value[len(self.namespace):]
                return f"hist:{short_name}"
            else:
                return f"<{value}>"

        elif value_type == "literal":
            datatype = value_dict.get("datatype", "")
            lang = value_dict.get("xml:lang", "")

            if datatype:
                # 데이터 타입이 있는 리터럴
                if "XMLSchema#integer" in datatype:
                    return f'"{value}"^^xsd:integer'
                elif "XMLSchema#string" in datatype:
                    return f'"{value}"^^xsd:string'
                else:
                    return f'"{value}"'
            elif lang:
                # 언어 태그가 있는 리터럴
                return f'"{value}"@{lang}'
            else:
                # 일반 리터럴
                return f'"{value}"'

        return ""

    def save_triples_to_file(
        self,
        inference_results: Dict[str, Any],
        output_path: str,
        session_id: str = None
    ) -> int:
        """
        추론 결과를 TTL 파일로 저장

        Args:
            inference_results: 추론 결과
            output_path: 출력 파일 경로
            session_id: 세션 ID

        Returns:
            생성된 Triple 개수
        """
        ttl_content = self.generate_ttl_from_inference_results(inference_results, session_id)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ttl_content)

        # Triple 개수 계산 (. 으로 끝나는 줄 개수)
        triple_count = ttl_content.count(" .")

        print(f"✅ 추론 결과 저장 완료: {output_path}")
        print(f"   - Triple 개수: {triple_count}")

        return triple_count

    def generate_inference_metadata(
        self,
        inference_results: Dict[str, Any],
        session_id: str,
        query: str,
        execution_time: float
    ) -> str:
        """
        추론 메타데이터 Triple 생성

        Args:
            inference_results: 추론 결과
            session_id: 세션 ID
            query: 사용자 질문
            execution_time: 실행 시간 (초)

        Returns:
            메타데이터 TTL
        """
        timestamp = datetime.now().isoformat()

        metadata_lines = [
            f"# 추론 메타데이터",
            f"",
            f"hist:InferenceSession_{session_id} a hist:InferenceSession ;",
            f'    hist:sessionId "{session_id}" ;',
            f'    hist:query "{query}" ;',
            f'    hist:timestamp "{timestamp}"^^xsd:dateTime ;',
            f'    hist:executionTime "{execution_time:.2f}"^^xsd:float ;'
        ]

        # 각 Thread별 통계
        for thread_type, result in inference_results.items():
            binding_count = len(result.get("bindings", []))
            status = result.get("status", "unknown")

            metadata_lines.append(
                f'    hist:thread_{thread_type}_status "{status}" ;'
            )
            metadata_lines.append(
                f'    hist:thread_{thread_type}_results "{binding_count}"^^xsd:integer ;'
            )

        # 마지막 세미콜론을 마침표로 변경
        metadata_lines[-1] = metadata_lines[-1].replace(" ;", " .")

        return "\n".join(metadata_lines)


# 사용 예시
if __name__ == "__main__":
    # 예시 추론 결과
    example_results = {
        "causal": {
            "status": "success",
            "bindings": [
                {
                    "cause": {"type": "uri", "value": "http://www.example.org/korean-history#Myeongnyang"},
                    "effect": {"type": "uri", "value": "http://www.example.org/korean-history#JapanRetreat"}
                }
            ]
        },
        "person": {
            "status": "success",
            "bindings": [
                {
                    "person": {"type": "uri", "value": "http://www.example.org/korean-history#YiSunSin"},
                    "event": {"type": "uri", "value": "http://www.example.org/korean-history#Myeongnyang"},
                    "role": {"type": "literal", "value": "Commander"}
                }
            ]
        }
    }

    generator = InferenceTripleGenerator()
    ttl = generator.generate_ttl_from_inference_results(example_results, "test_session")
    print(ttl)
