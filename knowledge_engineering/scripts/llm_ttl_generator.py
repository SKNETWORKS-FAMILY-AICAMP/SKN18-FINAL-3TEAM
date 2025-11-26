#!/usr/bin/env python3
"""
LLM을 사용한 TTL 자동 생성 스크립트

사용법:
    python llm_ttl_generator.py --input raw_data.txt --output generated.ttl

기능:
    1. 텍스트 데이터를 LLM에 전달
    2. LLM이 온톨로지 구조에 맞게 TTL 생성
    3. 자동으로 관계 추론 (leadsTo, causedBy 등)
"""

import os
import json
import argparse
from anthropic import Anthropic

# ============================================================
# LLM 기반 TTL 생성기
# ============================================================

class LLMTTLGenerator:
    def __init__(self, api_key=None):
        """
        LLM TTL 생성기 초기화

        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 읽음)
        """
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"

        # 온톨로지 스키마 정의 (프롬프트에 포함)
        self.ontology_schema = """
# 온톨로지 스키마

## 클래스
- Person: 역사적 인물
- Event: 역사적 사건
- Concept: 추상 개념
- Invention: 발명품
- Period: 시대
- Folktale: 민담/설화

## Object Properties
- leadsTo: 직접적 인과관계 (A가 B를 초래함)
- causedBy: 역방향 인과관계 (B가 A로 인해 발생)
- convergesTo: 수렴 관계 (여러 사건이 하나로 모임)
- relatedTo: 일반적 관련성

## Data Properties
- nodeName: 이름 (xsd:string)
- description: 설명 (xsd:string)
- year: 연도 (xsd:integer)
- order: 순서 (xsd:integer)
- chainId: 체인 ID (xsd:string)
- targetAudience: 대상 독자 (xsd:string)
"""

    def generate_ttl_from_text(self, raw_text, context=""):
        """
        텍스트로부터 TTL 생성

        Args:
            raw_text: 원본 텍스트 (역사 설명, 위키피디아 등)
            context: 추가 컨텍스트 (시대, 주제 등)

        Returns:
            생성된 TTL 문자열
        """
        prompt = f"""
당신은 한국사 온톨로지 전문가입니다. 주어진 텍스트를 분석하여 RDF Turtle (TTL) 형식으로 변환하세요.

{self.ontology_schema}

## 변환 규칙
1. 인물, 사건, 개념을 식별하고 적절한 클래스로 분류
2. 인과관계를 분석하여 leadsTo, causedBy 관계 생성
3. 연도, 설명 등 속성 추출
4. URI는 한글을 영어로 변환 (예: 임진왜란 → ImjinWar)

## 입력 텍스트
{raw_text}

## 추가 컨텍스트
{context}

## 출력 형식
반드시 아래 형식으로만 출력하세요:

```turtle
@prefix hist: <http://example.org/history#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# 여기에 TTL 데이터 작성
```

JSON이나 다른 설명 없이 TTL 코드만 출력하세요.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # 응답에서 TTL 추출
        ttl_content = response.content[0].text

        # ```turtle 블록 제거
        if "```turtle" in ttl_content:
            ttl_content = ttl_content.split("```turtle")[1].split("```")[0].strip()
        elif "```" in ttl_content:
            ttl_content = ttl_content.split("```")[1].split("```")[0].strip()

        return ttl_content

    def generate_ttl_from_json(self, json_data):
        """
        JSON 데이터로부터 TTL 생성 (구조화된 데이터용)

        Args:
            json_data: JSON 형식의 구조화된 데이터

        Returns:
            생성된 TTL 문자열
        """
        prompt = f"""
당신은 한국사 온톨로지 전문가입니다. 주어진 JSON 데이터를 RDF Turtle (TTL) 형식으로 변환하세요.

{self.ontology_schema}

## JSON 데이터
```json
{json.dumps(json_data, ensure_ascii=False, indent=2)}
```

## 출력 형식
반드시 아래 형식으로만 출력하세요:

```turtle
@prefix hist: <http://example.org/history#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# 여기에 TTL 데이터 작성
```

JSON이나 다른 설명 없이 TTL 코드만 출력하세요.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        ttl_content = response.content[0].text

        # ```turtle 블록 제거
        if "```turtle" in ttl_content:
            ttl_content = ttl_content.split("```turtle")[1].split("```")[0].strip()
        elif "```" in ttl_content:
            ttl_content = ttl_content.split("```")[1].split("```")[0].strip()

        return ttl_content

    def batch_generate(self, input_file, output_file, format="text"):
        """
        파일로부터 배치 생성

        Args:
            input_file: 입력 파일 (txt 또는 json)
            output_file: 출력 TTL 파일
            format: "text" 또는 "json"
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            if format == "json":
                data = json.load(f)
                ttl_content = self.generate_ttl_from_json(data)
            else:
                text = f.read()
                ttl_content = self.generate_ttl_from_text(text)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ttl_content)

        print(f"✅ TTL 생성 완료: {output_file}")


# ============================================================
# 사용 예시
# ============================================================

def example_text_to_ttl():
    """텍스트에서 TTL 생성 예시"""

    generator = LLMTTLGenerator()

    raw_text = """
    1592년, 도요토미 히데요시가 조선을 침략하여 임진왜란이 발발했다.
    이에 맞서 이순신 장군이 수군을 이끌고 한산도 대첩에서 대승을 거두었다.
    이순신의 활약으로 일본군은 큰 타격을 입었고, 전쟁은 장기화되었다.
    """

    ttl = generator.generate_ttl_from_text(raw_text, context="임진왜란 시대")

    print("생성된 TTL:")
    print(ttl)

    # 파일로 저장
    with open('generated_example.ttl', 'w', encoding='utf-8') as f:
        f.write(ttl)


def example_json_to_ttl():
    """JSON에서 TTL 생성 예시"""

    generator = LLMTTLGenerator()

    json_data = {
        "events": [
            {
                "id": "imjin_war",
                "name": "임진왜란",
                "year": 1592,
                "description": "도요토미 히데요시의 조선 침략",
                "type": "Event",
                "leadsTo": ["yi_sun_sin_appointed"]
            },
            {
                "id": "yi_sun_sin_appointed",
                "name": "이순신 수군통제사 임명",
                "year": 1592,
                "description": "조선 수군의 리더십 확립",
                "type": "Event",
                "leadsTo": ["hansando_victory"]
            },
            {
                "id": "hansando_victory",
                "name": "한산도 대첩",
                "year": 1592,
                "description": "이순신의 학익진 전법으로 대승",
                "type": "Event"
            }
        ]
    }

    ttl = generator.generate_ttl_from_json(json_data)

    print("생성된 TTL:")
    print(ttl)


def example_batch_wikipedia():
    """위���피디아 텍스트를 TTL로 변환"""

    generator = LLMTTLGenerator()

    wiki_text = """
    조선 태조 이성계(1335~1408)는 고려 말 무신으로, 위화도 회군을 통해
    권력을 장악한 후 1392년 조선을 건국했다. 이성계는 신진 사대부 세력과
    연합하여 고려 왕조를 무너뜨리고 새로운 왕조를 세웠다. 조선은 성리학을
    통치 이념으로 채택하고, 한양을 새로운 수도로 정했다.
    """

    # 파일로 저장
    with open('temp_wiki_input.txt', 'w', encoding='utf-8') as f:
        f.write(wiki_text)

    generator.batch_generate(
        'temp_wiki_input.txt',
        'wiki_generated.ttl',
        format='text'
    )


# ============================================================
# CLI 인터페이스
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='LLM을 사용한 TTL 자동 생성 도구'
    )

    parser.add_argument(
        '--input',
        type=str,
        help='입력 파일 (txt 또는 json)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='출력 TTL 파일'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'json'],
        default='text',
        help='입력 형식 (기본값: text)'
    )

    parser.add_argument(
        '--example',
        type=str,
        choices=['text', 'json', 'wiki'],
        help='예시 실행'
    )

    args = parser.parse_args()

    # 예시 실행
    if args.example:
        if args.example == 'text':
            example_text_to_ttl()
        elif args.example == 'json':
            example_json_to_ttl()
        elif args.example == 'wiki':
            example_batch_wikipedia()
        return

    # 실제 파일 처리
    if not args.input or not args.output:
        parser.print_help()
        return

    generator = LLMTTLGenerator()
    generator.batch_generate(args.input, args.output, args.format)


if __name__ == '__main__':
    main()
