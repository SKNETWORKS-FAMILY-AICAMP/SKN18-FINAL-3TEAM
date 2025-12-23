"""
Intent별 테스트 질문 생성

intent_router의 4가지 query_type에 적합한 질문을 생성:
- factual: 사실 확인 질문
- causal: 인과관계 질문
- comparative: 비교 질문
- deep_analysis: 심층 분석 질문
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TestQuery:
    """테스트 질문"""
    query: str
    query_type: str  # factual, causal, comparative, deep_analysis
    intent_keywords: List[str]  # 질문 의도 키워드
    expected_entities: List[str]  # 예상되는 핵심 엔티티
    difficulty: str  # easy, medium, hard
    description: str  # 질문 설명


class PersonaQueryBuilder:
    """Intent별 테스트 질문 생성기"""

    @staticmethod
    def build_factual_queries() -> List[TestQuery]:
        """Factual 질문 생성 (사실 확인)"""
        return [
            TestQuery(
                query="세종대왕이 훈민정음을 창제한 시기는 언제인가?",
                query_type="factual",
                intent_keywords=["시기", "언제", "창제"],
                expected_entities=["세종", "훈민정음"],
                difficulty="easy",
                description="단순 사실 확인 - 시간 정보"
            ),
            TestQuery(
                query="이순신이 참전한 전투는 무엇이 있는가?",
                query_type="factual",
                intent_keywords=["참전", "전투"],
                expected_entities=["이순신"],
                difficulty="easy",
                description="단순 사실 확인 - 관계 정보"
            ),
            TestQuery(
                query="경복궁은 누가 건설했는가?",
                query_type="factual",
                intent_keywords=["건설", "누가"],
                expected_entities=["경복궁"],
                difficulty="easy",
                description="단순 사실 확인 - 주체 정보"
            ),
            TestQuery(
                query="광해군의 재위 기간은?",
                query_type="factual",
                intent_keywords=["재위 기간"],
                expected_entities=["광해군"],
                difficulty="easy",
                description="단순 사실 확인 - 기간 정보"
            ),
            TestQuery(
                query="정약용이 저술한 책의 제목은?",
                query_type="factual",
                intent_keywords=["저술", "책"],
                expected_entities=["정약용"],
                difficulty="medium",
                description="사실 확인 - 다중 답변 가능"
            ),
            TestQuery(
                query="임진왜란은 몇 년도에 발생했는가?",
                query_type="factual",
                intent_keywords=["몇 년도", "발생"],
                expected_entities=["임진왜란"],
                difficulty="easy",
                description="단순 사실 확인 - 연도 정보"
            ),
            TestQuery(
                query="한석봉의 본명은 무엇인가?",
                query_type="factual",
                intent_keywords=["본명"],
                expected_entities=["한석봉"],
                difficulty="easy",
                description="단순 사실 확인 - 별칭/본명"
            ),
            TestQuery(
                query="병자호란 당시 조선의 왕은 누구인가?",
                query_type="factual",
                intent_keywords=["당시", "왕", "누구"],
                expected_entities=["병자호란"],
                difficulty="easy",
                description="사실 확인 - 시간적 맥락"
            ),
            TestQuery(
                query="불국사는 어느 시대에 건립되었는가?",
                query_type="factual",
                intent_keywords=["어느 시대", "건립"],
                expected_entities=["불국사"],
                difficulty="medium",
                description="사실 확인 - 시대 정보"
            ),
            TestQuery(
                query="을사조약은 언제 체결되었는가?",
                query_type="factual",
                intent_keywords=["언제", "체결"],
                expected_entities=["을사조약"],
                difficulty="easy",
                description="단순 사실 확인 - 조약 시기"
            ),
        ]

    @staticmethod
    def build_causal_queries() -> List[TestQuery]:
        """Causal 질문 생성 (인과관계)"""
        return [
            TestQuery(
                query="임진왜란이 발생한 원인은 무엇인가?",
                query_type="causal",
                intent_keywords=["원인", "발생", "이유"],
                expected_entities=["임진왜란"],
                difficulty="medium",
                description="인과관계 - 전쟁의 원인"
            ),
            TestQuery(
                query="세종대왕이 훈민정음을 창제한 이유는?",
                query_type="causal",
                intent_keywords=["이유", "창제"],
                expected_entities=["세종", "훈민정음"],
                difficulty="medium",
                description="인과관계 - 정책의 동기"
            ),
            TestQuery(
                query="인조반정이 일어나게 된 배경은 무엇인가?",
                query_type="causal",
                intent_keywords=["배경", "일어나다"],
                expected_entities=["인조반정"],
                difficulty="medium",
                description="인과관계 - 정변의 배경"
            ),
            TestQuery(
                query="고려가 몽골에 항복한 이유는?",
                query_type="causal",
                intent_keywords=["이유", "항복"],
                expected_entities=["고려", "몽골"],
                difficulty="hard",
                description="인과관계 - 2개 엔티티 관계 (수렴 노드 중요)"
            ),
            TestQuery(
                query="병자호란의 결과로 조선에 어떤 영향을 끼쳤는가?",
                query_type="causal",
                intent_keywords=["결과", "영향"],
                expected_entities=["병자호란", "조선"],
                difficulty="hard",
                description="인과관계 - 전쟁의 결과 (수렴 노드 중요)"
            ),
            TestQuery(
                query="정조가 수원 화성을 건설한 목적은?",
                query_type="causal",
                intent_keywords=["목적", "건설"],
                expected_entities=["정조", "화성"],
                difficulty="medium",
                description="인과관계 - 건설의 목적"
            ),
            TestQuery(
                query="갑신정변이 실패한 원인은 무엇인가?",
                query_type="causal",
                intent_keywords=["원인", "실패"],
                expected_entities=["갑신정변"],
                difficulty="medium",
                description="인과관계 - 실패 원인"
            ),
            TestQuery(
                query="신라가 삼국을 통일할 수 있었던 이유는?",
                query_type="causal",
                intent_keywords=["이유", "통일"],
                expected_entities=["신라", "삼국통일"],
                difficulty="hard",
                description="인과관계 - 통일의 요인"
            ),
            TestQuery(
                query="동학농민운동이 확산된 배경은?",
                query_type="causal",
                intent_keywords=["배경", "확산"],
                expected_entities=["동학농민운동"],
                difficulty="medium",
                description="인과관계 - 운동의 확산 배경"
            ),
            TestQuery(
                query="조선시대 당쟁이 격화된 원인은 무엇인가?",
                query_type="causal",
                intent_keywords=["원인", "격화"],
                expected_entities=["조선", "당쟁"],
                difficulty="hard",
                description="인과관계 - 정치 갈등의 원인"
            ),
        ]

    @staticmethod
    def build_comparative_queries() -> List[TestQuery]:
        """Comparative 질문 생성 (비교)"""
        return [
            TestQuery(
                query="임진왜란과 병자호란의 공통점은 무엇인가?",
                query_type="comparative",
                intent_keywords=["공통점", "비교"],
                expected_entities=["임진왜란", "병자호란"],
                difficulty="hard",
                description="비교 질문 - 2개 전쟁 공통점 (수렴 노드 매우 중요)"
            ),
            TestQuery(
                query="세종대왕과 정조의 업적을 비교하면?",
                query_type="comparative",
                intent_keywords=["비교", "업적"],
                expected_entities=["세종", "정조"],
                difficulty="hard",
                description="비교 질문 - 2명의 왕 업적 (수렴 노드 중요)"
            ),
            TestQuery(
                query="갑오개혁과 갑신정변의 차이점은?",
                query_type="comparative",
                intent_keywords=["차이점", "비교"],
                expected_entities=["갑오개혁", "갑신정변"],
                difficulty="hard",
                description="비교 질문 - 2개 개혁 차이점 (수렴 노드 중요)"
            ),
            TestQuery(
                query="신라와 고구려의 건국 과정의 유사점은?",
                query_type="comparative",
                intent_keywords=["유사점", "건국"],
                expected_entities=["신라", "고구려"],
                difficulty="hard",
                description="비교 질문 - 건국 과정 비교 (수렴 노드 중요)"
            ),
            TestQuery(
                query="훈민정음과 한자의 차이는 무엇인가?",
                query_type="comparative",
                intent_keywords=["차이", "비교"],
                expected_entities=["훈민정음", "한자"],
                difficulty="medium",
                description="비교 질문 - 문자 체계 비교"
            ),
            TestQuery(
                query="이순신과 권율의 전략 차이는?",
                query_type="comparative",
                intent_keywords=["차이", "전략"],
                expected_entities=["이순신", "권율"],
                difficulty="hard",
                description="비교 질문 - 장군 전략 비교 (수렴 노드 중요)"
            ),
            TestQuery(
                query="조선 전기와 후기의 정치 체제 차이는?",
                query_type="comparative",
                intent_keywords=["차이", "정치"],
                expected_entities=["조선"],
                difficulty="hard",
                description="비교 질문 - 시대별 정치 체제"
            ),
            TestQuery(
                query="백제와 신라의 불교 수용 방식 차이는?",
                query_type="comparative",
                intent_keywords=["차이", "수용"],
                expected_entities=["백제", "신라", "불교"],
                difficulty="hard",
                description="비교 질문 - 종교 수용 비교"
            ),
            TestQuery(
                query="경복궁과 창덕궁의 건축 양식 차이는?",
                query_type="comparative",
                intent_keywords=["차이", "건축"],
                expected_entities=["경복궁", "창덕궁"],
                difficulty="medium",
                description="비교 질문 - 건축물 비교"
            ),
            TestQuery(
                query="동학과 천주교의 사상적 공통점은?",
                query_type="comparative",
                intent_keywords=["공통점", "사상"],
                expected_entities=["동학", "천주교"],
                difficulty="hard",
                description="비교 질문 - 종교 사상 비교 (수렴 노드 중요)"
            ),
        ]

    @staticmethod
    def build_deep_analysis_queries() -> List[TestQuery]:
        """Deep Analysis 질문 생성 (심층 분석)"""
        return [
            TestQuery(
                query="세종대왕의 업적이 조선 사회에 미친 영향을 분석하라",
                query_type="deep_analysis",
                intent_keywords=["업적", "영향", "분석"],
                expected_entities=["세종", "조선"],
                difficulty="hard",
                description="심층 분석 - 업적의 사회적 영향"
            ),
            TestQuery(
                query="임진왜란이 조선 사회 전반에 끼친 장기적 영향은?",
                query_type="deep_analysis",
                intent_keywords=["영향", "장기적"],
                expected_entities=["임진왜란", "조선"],
                difficulty="hard",
                description="심층 분석 - 전쟁의 장기 영향 (수렴 노드 중요)"
            ),
            TestQuery(
                query="조선시대 당쟁의 전개 과정과 그 영향을 설명하라",
                query_type="deep_analysis",
                intent_keywords=["과정", "영향", "설명"],
                expected_entities=["조선", "당쟁"],
                difficulty="hard",
                description="심층 분석 - 정치 갈등의 전개"
            ),
            TestQuery(
                query="고려의 대몽항쟁이 고려 사회에 미친 영향은?",
                query_type="deep_analysis",
                intent_keywords=["영향", "항쟁"],
                expected_entities=["고려", "몽골"],
                difficulty="hard",
                description="심층 분석 - 항쟁의 사회적 영향 (수렴 노드 중요)"
            ),
            TestQuery(
                query="실학사상의 발전 과정과 조선 후기 사회 변화의 관계를 분석하라",
                query_type="deep_analysis",
                intent_keywords=["과정", "관계", "분석"],
                expected_entities=["실학", "조선"],
                difficulty="hard",
                description="심층 분석 - 사상과 사회 변화"
            ),
            TestQuery(
                query="신라의 삼국통일 과정에서 나타난 외교 전략을 분석하라",
                query_type="deep_analysis",
                intent_keywords=["과정", "전략", "분석"],
                expected_entities=["신라", "삼국통일"],
                difficulty="hard",
                description="심층 분석 - 외교 전략 분석"
            ),
            TestQuery(
                query="조선 건국의 정당성 확립 과정을 설명하라",
                query_type="deep_analysis",
                intent_keywords=["과정", "정당성", "설명"],
                expected_entities=["조선"],
                difficulty="hard",
                description="심층 분석 - 왕조 건국 과정"
            ),
            TestQuery(
                query="대한제국의 성립 배경과 한계를 분석하라",
                query_type="deep_analysis",
                intent_keywords=["배경", "한계", "분석"],
                expected_entities=["대한제국"],
                difficulty="hard",
                description="심층 분석 - 정치 체제 변화"
            ),
            TestQuery(
                query="이순신의 전략적 사고가 해전에 미친 영향을 분석하라",
                query_type="deep_analysis",
                intent_keywords=["전략", "영향", "분석"],
                expected_entities=["이순신"],
                difficulty="hard",
                description="심층 분석 - 인물의 전략적 영향"
            ),
            TestQuery(
                query="조선 후기 민란의 발생 원인과 사회 변화의 관계를 설명하라",
                query_type="deep_analysis",
                intent_keywords=["원인", "관계", "설명"],
                expected_entities=["조선", "민란"],
                difficulty="hard",
                description="심층 분석 - 사회 갈등과 변화 (수렴 노드 중요)"
            ),
        ]

    @staticmethod
    def build_all_queries() -> List[TestQuery]:
        """모든 Intent별 질문 생성 (총 40개)"""
        all_queries = []
        all_queries.extend(PersonaQueryBuilder.build_factual_queries())       # 10개
        all_queries.extend(PersonaQueryBuilder.build_causal_queries())        # 10개
        all_queries.extend(PersonaQueryBuilder.build_comparative_queries())   # 10개
        all_queries.extend(PersonaQueryBuilder.build_deep_analysis_queries()) # 10개
        return all_queries

    @staticmethod
    def save_to_json(output_path: str):
        """질문을 JSON 파일로 저장"""
        queries = PersonaQueryBuilder.build_all_queries()

        # TestQuery -> dict 변환
        queries_dict = [
            {
                "query": q.query,
                "query_type": q.query_type,
                "intent_keywords": q.intent_keywords,
                "expected_entities": q.expected_entities,
                "difficulty": q.difficulty,
                "description": q.description
            }
            for q in queries
        ]

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(queries_dict, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(queries)}개 질문 저장: {output_file}")
        print(f"\nQuery Type 분포:")
        type_counts = {}
        for q in queries:
            type_counts[q.query_type] = type_counts.get(q.query_type, 0) + 1

        for qtype, count in type_counts.items():
            print(f"  - {qtype}: {count}개")


if __name__ == "__main__":
    # 질문 생성 및 저장
    PersonaQueryBuilder.save_to_json("data/test_queries.json")
