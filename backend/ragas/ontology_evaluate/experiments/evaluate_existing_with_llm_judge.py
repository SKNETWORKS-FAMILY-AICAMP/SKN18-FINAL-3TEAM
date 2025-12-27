"""
기존 Ablation/Isolation 실험 결과에 LLM Judge 평가 추가

Target directories:
- backend/ragas/ontology_evaluate/data/results_ablation
- backend/ragas/ontology_evaluate/data/results_isolation

평가 모델: gpt-5-mini (DO NOT CHANGE)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / ".env")


class AnswerQualityJudge:
    """답변 품질 평가 LLM Judge"""

    def __init__(self, model: str = None, api_key: str = None):
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def evaluate_answer_quality(
        self,
        query: str,
        query_type: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        답변 품질 종합 평가

        Returns:
            {
                "completeness": 0.0~1.0,      # 질문에 충분히 답했는가
                "information_richness": 0.0~1.0,  # 추가 유용 정보 제공
                "factual_accuracy": 0.0~1.0,  # 사실적 정확성 (역사적 사실)
                "coherence": 0.0~1.0,         # 논리적 일관성
                "helpfulness": 0.0~1.0,       # 사용자에게 실제 도움
                "overall_score": 0.0~1.0,     # 종합 점수
                "reasoning": str              # 평가 근거
            }
        """
        prompt = f"""당신은 한국사 전문가이자 RAG 시스템 평가자입니다.

질문: {query}
질문 유형: {query_type}

시스템 답변:
{answer}

다음 기준으로 답변 품질을 평가하세요 (각 0.0~1.0):

1. **completeness** (완성도): 질문에 충분히 답했는가?
   - 1.0: 질문의 모든 측면에 완벽히 답함
   - 0.5: 핵심은 답했지만 일부 누락
   - 0.0: 질문에 제대로 답하지 못함

2. **information_richness** (정보 풍부함): 추가로 유용한 정보를 제공했는가?
   - 1.0: 관련 배경, 맥락, 연결 정보까지 풍부하게 제공
   - 0.5: 기본 정보만 제공
   - 0.0: 정보가 빈약함

3. **factual_accuracy** (사실 정확성): 역사적 사실과 일치하는가?
   - 1.0: 모든 내용이 사실과 일치
   - 0.5: 대부분 맞지만 일부 오류
   - 0.0: 심각한 사실 오류

4. **coherence** (논리성): 답변이 논리적으로 일관되는가?
   - 1.0: 논리적으로 완벽하게 연결됨
   - 0.5: 대체로 논리적이지만 일부 비약
   - 0.0: 논리적 연결이 부족

5. **helpfulness** (유용성): 사용자에게 실제로 도움이 되는가?
   - 1.0: 매우 도움됨, 이해하기 쉬움
   - 0.5: 어느 정도 도움됨
   - 0.0: 도움이 안 됨

다음 JSON 형식으로만 응답하세요:
{{
    "completeness": 0.X,
    "information_richness": 0.X,
    "factual_accuracy": 0.X,
    "coherence": 0.X,
    "helpfulness": 0.X,
    "reasoning": "평가 근거 요약 (2-3문장)"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # overall_score 계산 (가중 평균)
            weights = {
                "completeness": 0.25,
                "information_richness": 0.20,
                "factual_accuracy": 0.25,
                "coherence": 0.15,
                "helpfulness": 0.15
            }

            overall = sum(
                result.get(k, 0) * w
                for k, w in weights.items()
            )
            result["overall_score"] = round(overall, 4)

            return result

        except Exception as e:
            return {
                "completeness": 0,
                "information_richness": 0,
                "factual_accuracy": 0,
                "coherence": 0,
                "helpfulness": 0,
                "overall_score": 0,
                "reasoning": f"평가 실패: {str(e)}",
                "error": True
            }


def evaluate_single_file(
    input_file: Path,
    output_file: Path,
    judge: AnswerQualityJudge
):
    """
    단일 결과 파일에 LLM Judge 평가 추가

    Args:
        input_file: 입력 JSON 파일
        output_file: 출력 JSON 파일
        judge: AnswerQualityJudge 인스턴스
    """
    print(f"\n📂 처리 중: {input_file.name}")

    # 결과 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    if not isinstance(results, list):
        print(f"  ⚠️  리스트 형식이 아닙니다. 스킵.")
        return

    print(f"  총 {len(results)}개 결과 평가 시작...")

    evaluated_results = []
    success_count = 0
    skip_count = 0

    for i, r in enumerate(results):
        query = r.get("query", "")
        query_type = r.get("state_output", {}).get("query_type", "factual")

        # final_answer 추출 (여러 위치 확인)
        answer = (
            r.get("final_answer") or
            r.get("state_output", {}).get("final_answer") or
            r.get("answer", "")
        )

        if not answer:
            print(f"  [{i+1}/{len(results)}] 답변 없음, 스킵")
            skip_count += 1
            r["llm_judge_quality"] = {
                "error": True,
                "reasoning": "답변 없음"
            }
            evaluated_results.append(r)
            continue

        print(f"  [{i+1}/{len(results)}] 평가 중: {query[:40]}...")

        # LLM Judge 평가
        quality_eval = judge.evaluate_answer_quality(query, query_type, answer)

        # 기존 결과에 추가
        r["llm_judge_quality"] = quality_eval
        evaluated_results.append(r)

        if not quality_eval.get("error"):
            success_count += 1
            print(f"    → overall_score: {quality_eval.get('overall_score', 'N/A'):.4f}")

    # 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluated_results, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 완료: {output_file.name}")
    print(f"     성공: {success_count}개, 스킵: {skip_count}개")

    # 요약 통계
    scores = [
        r["llm_judge_quality"]["overall_score"]
        for r in evaluated_results
        if "llm_judge_quality" in r and not r["llm_judge_quality"].get("error")
    ]

    if scores:
        print(f"     평균 점수: {sum(scores)/len(scores):.4f} (min: {min(scores):.4f}, max: {max(scores):.4f})")


def process_directory(
    input_dir: Path,
    output_dir: Path,
    file_pattern: str = "*_full.json"
):
    """
    디렉토리 내 모든 결과 파일 처리

    Args:
        input_dir: 입력 디렉토리
        output_dir: 출력 디렉토리
        file_pattern: 처리할 파일 패턴 (기본: *_full.json)
    """
    print("\n" + "="*70)
    print(f"📁 디렉토리 처리: {input_dir.name}")
    print("="*70)

    # Judge 초기화
    judge = AnswerQualityJudge()
    print(f"🤖 LLM Judge 모델: {judge.model}")

    # 파일 찾기
    input_files = sorted(input_dir.glob(file_pattern))

    if not input_files:
        print(f"⚠️  패턴 '{file_pattern}'에 해당하는 파일이 없습니다.")
        return

    print(f"📊 처리 대상: {len(input_files)}개 파일")
    for f in input_files:
        print(f"  - {f.name}")

    # 각 파일 처리
    for input_file in input_files:
        # 출력 파일명: 원본명 + _with_llm_judge
        output_filename = input_file.stem + "_with_llm_judge.json"
        output_file = output_dir / output_filename

        evaluate_single_file(input_file, output_file, judge)

    print("\n" + "="*70)
    print(f"✅ {input_dir.name} 처리 완료!")
    print("="*70)


def main():
    """Main 실행 함수"""

    print("\n" + "="*70)
    print("LLM Judge 평가 - 기존 Ablation/Isolation 결과")
    print("="*70)
    print()

    # 경로 설정
    base_dir = PROJECT_ROOT / "backend" / "ragas" / "ontology_evaluate" / "data"

    ablation_input_dir = base_dir / "results_ablation"
    ablation_output_dir = base_dir / "results_ablation_llm_judge"

    isolation_input_dir = base_dir / "results_isolation"
    isolation_output_dir = base_dir / "results_isolation_llm_judge"

    # 1. Ablation 결과 처리
    if ablation_input_dir.exists():
        process_directory(
            input_dir=ablation_input_dir,
            output_dir=ablation_output_dir,
            file_pattern="*_full.json"
        )
    else:
        print(f"⚠️  {ablation_input_dir} 디렉토리가 없습니다.")

    print("\n")

    # 2. Isolation 결과 처리
    if isolation_input_dir.exists():
        process_directory(
            input_dir=isolation_input_dir,
            output_dir=isolation_output_dir,
            file_pattern="*_full.json"
        )
    else:
        print(f"⚠️  {isolation_input_dir} 디렉토리가 없습니다.")

    # 최종 요약
    print("\n" + "="*70)
    print("🎉 모든 처리 완료!")
    print("="*70)
    print()
    print("📂 출력 디렉토리:")
    print(f"  - {ablation_output_dir}")
    print(f"  - {isolation_output_dir}")
    print()
    print("다음 단계: 결과 분석")
    print("  python -m backend.ragas.ontology_evaluate.experiments.analyze_llm_judge_results")
    print()


if __name__ == "__main__":
    main()
