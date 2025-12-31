"""
온톨로지 스키마 로더

korean_history.owl 파일에서 클래스와 프로퍼티를 추출하여
평가에 사용할 수 있는 스키마 딕셔너리로 변환
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set


class OntologySchemaLoader:
    """OWL 파일에서 온톨로지 스키마를 로드"""

    # RDF/OWL 네임스페이스
    NAMESPACES = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'hist': 'http://www.example.org/korean-history#'
    }

    @staticmethod
    def load_from_owl(owl_path: str) -> Dict:
        """
        OWL 파일에서 온톨로지 스키마 로드

        Args:
            owl_path: korean_history.owl 파일 경로

        Returns:
            {
                "classes": ["Person", "Event", ...],
                "properties": {
                    "participatesIn": {"domain": "Person", "range": "Event"},
                    ...
                }
            }
        """
        owl_file = Path(owl_path)
        if not owl_file.exists():
            raise FileNotFoundError(f"OWL 파일을 찾을 수 없습니다: {owl_path}")

        # XML 파싱
        tree = ET.parse(owl_file)
        root = tree.getroot()

        # 클래스 추출
        classes = OntologySchemaLoader._extract_classes(root)

        # 프로퍼티 추출
        properties = OntologySchemaLoader._extract_properties(root, classes)

        return {
            "classes": classes,
            "properties": properties
        }

    @staticmethod
    def _extract_classes(root: ET.Element) -> List[str]:
        """
        OWL에서 클래스 추출

        Returns:
            ["Person", "Event", "Place", ...]
        """
        classes = []

        # owl:Class 태그 찾기
        for class_elem in root.findall('.//owl:Class', OntologySchemaLoader.NAMESPACES):
            about = class_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
            if about:
                # http://www.example.org/korean-history#Person → Person
                class_name = about.split('#')[-1]
                classes.append(class_name)

        return sorted(classes)

    @staticmethod
    def _extract_properties(root: ET.Element, classes: List[str]) -> Dict[str, Dict]:
        """
        OWL에서 ObjectProperty 추출 및 domain/range 추론

        Args:
            root: XML root
            classes: 추출된 클래스 리스트

        Returns:
            {
                "participatesIn": {"domain": "Person", "range": "Event"},
                "leadsTo": {"domain": "Event", "range": "Event"},
                ...
            }
        """
        properties = {}

        # owl:ObjectProperty 태그 찾기
        for prop_elem in root.findall('.//owl:ObjectProperty', OntologySchemaLoader.NAMESPACES):
            about = prop_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
            if about:
                prop_name = about.split('#')[-1]

                # rdfs:domain과 rdfs:range 추출 (OWL에 명시된 경우)
                domain_elem = prop_elem.find('rdfs:domain', OntologySchemaLoader.NAMESPACES)
                range_elem = prop_elem.find('rdfs:range', OntologySchemaLoader.NAMESPACES)

                domain = None
                range_val = None

                if domain_elem is not None:
                    domain_resource = domain_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                    if domain_resource:
                        domain = domain_resource.split('#')[-1]

                if range_elem is not None:
                    range_resource = range_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                    if range_resource:
                        range_val = range_resource.split('#')[-1]

                # rdfs:comment에서 힌트 추출 (명시적 domain/range가 없는 경우)
                if domain is None or range_val is None:
                    comment_elem = prop_elem.find('rdfs:comment', OntologySchemaLoader.NAMESPACES)
                    if comment_elem is not None and comment_elem.text:
                        comment = comment_elem.text
                        inferred_domain, inferred_range = OntologySchemaLoader._infer_domain_range_from_comment(
                            prop_name, comment, classes
                        )
                        domain = domain or inferred_domain
                        range_val = range_val or inferred_range

                # 프로퍼티 정보 저장
                if domain or range_val:
                    properties[prop_name] = {}
                    if domain:
                        properties[prop_name]["domain"] = domain
                    if range_val:
                        properties[prop_name]["range"] = range_val

        return properties

    @staticmethod
    def _infer_domain_range_from_comment(
        prop_name: str,
        comment: str,
        classes: List[str]
    ) -> tuple:
        """
        rdfs:comment에서 domain과 range 추론

        Args:
            prop_name: 프로퍼티 이름
            comment: rdfs:comment 텍스트 (예: "인물이 사건에 참여하다")
            classes: 클래스 리스트

        Returns:
            (domain, range) 튜플
        """
        domain = None
        range_val = None

        # 휴리스틱 규칙
        comment_lower = comment.lower()

        # Domain 추론
        if '인물이' in comment or '사람이' in comment:
            domain = 'Person'
        elif '사건이' in comment:
            domain = 'Event'
        elif '기관이' in comment or '제도가' in comment:
            domain = 'Institution'
        elif '국가가' in comment:
            domain = 'Nation'
        elif '장소가' in comment:
            domain = 'Place'

        # Range 추론
        if '사건' in comment and domain != 'Event':
            range_val = 'Event'
        elif '인물' in comment and domain != 'Person':
            range_val = 'Person'
        elif '문헌' in comment:
            range_val = 'Document'
        elif '기관' in comment or '제도' in comment:
            range_val = 'Institution'
        elif '국가' in comment:
            range_val = 'Nation'
        elif '장소' in comment:
            range_val = 'Place'

        # 특정 프로퍼티 패턴 (causal chain 관련)
        if prop_name in ['leadsTo', 'ledTo', 'causes', 'derivedFrom']:
            # 인과관계는 주로 Event → Event
            domain = domain or 'Event'
            range_val = range_val or 'Event'

        # 학문 관계
        if prop_name in ['studentOf', 'teacherOf']:
            domain = 'Person'
            range_val = 'Person'

        if prop_name in ['authored', 'compiled']:
            domain = 'Person'
            range_val = 'Document'

        # 참여 관계
        if prop_name == 'participatesIn':
            domain = 'Person'
            range_val = 'Event'

        if prop_name == 'involvesPerson':
            domain = 'Event'
            range_val = 'Person'

        return domain, range_val

    @staticmethod
    def load_default_schema() -> Dict:
        """
        기본 온톨로지 스키마 로드 (korean_history.owl)

        Returns:
            온톨로지 스키마 딕셔너리
        """
        # 프로젝트 루트에서 OWL 파일 경로 찾기
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent  # backend까지 올라감

        owl_path = project_root / 'langgraph_fuseki' / 'ontology' / 'korean_history.owl'

        if not owl_path.exists():
            # Fallback: 하드코딩된 기본 스키마
            print(f"⚠️  OWL 파일을 찾을 수 없습니다: {owl_path}")
            print("   하드코딩된 기본 스키마를 사용합니다.")
            return OntologySchemaLoader._get_fallback_schema()

        try:
            schema = OntologySchemaLoader.load_from_owl(str(owl_path))
            print(f"✅ 온톨로지 스키마 로드 완료: {len(schema['classes'])}개 클래스, {len(schema['properties'])}개 프로퍼티")
            return schema
        except Exception as e:
            print(f"⚠️  OWL 파일 파싱 실패: {e}")
            print("   하드코딩된 기본 스키마를 사용합니다.")
            return OntologySchemaLoader._get_fallback_schema()

    @staticmethod
    def _get_fallback_schema() -> Dict:
        """Fallback 기본 스키마 (OWL 파일을 찾을 수 없을 때)"""
        return {
            "classes": [
                "Battle", "Document", "Event", "Institution",
                "Nation", "Object", "Person", "Place",
                "Policy", "Role", "SocialClass"
            ],
            "properties": {
                "participatesIn": {"domain": "Person", "range": "Event"},
                "involvesPerson": {"domain": "Event", "range": "Person"},
                "leadsTo": {"domain": "Event", "range": "Event"},
                "ledTo": {"domain": "Event", "range": "Event"},
                "causes": {"domain": "Event", "range": "Event"},
                "authored": {"domain": "Person", "range": "Document"},
                "compiled": {"domain": "Person", "range": "Document"},
                "studentOf": {"domain": "Person", "range": "Person"},
                "teacherOf": {"domain": "Person", "range": "Person"},
                "servedUnder": {"domain": "Person", "range": "Person"},
                "contemporaryWith": {"domain": "Person", "range": "Person"},
                "affiliatedWith": {"domain": "Person", "range": "Nation"},
                "built": {"domain": "Person", "range": "Place"},
                "established": {"domain": "Person", "range": "Institution"},
                "founded": {"domain": "Person", "range": "Institution"}
            }
        }


# 편의 함수
def load_ontology_schema() -> Dict:
    """온톨로지 스키마 로드 (편의 함수)"""
    return OntologySchemaLoader.load_default_schema()
