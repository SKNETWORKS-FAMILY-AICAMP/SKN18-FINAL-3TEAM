"""
기존 batch 결과 파일에 LLM Judge 평가 추가

사용법:
    python -m backend.ragas.ontology_evaluate.experiments.add_llm_judge_to_batch \
        --input-file backend/ragas/ontology_evaluate/data/query_type_aware_results/batch_1_results_20251229_141730.json \
        --output-file backend/ragas/ontology_evaluate/data/query_type_aware_results/batch_1_results_20251229_141730.json
"""

import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.experiment_utils import load_queries


def needs_llm_judge(result: Dict[str, Any]) -> bool:
    """LLM Judge 평가가 필요한지 확인"""
    llm_judge_quality = result.get("llm_judge_quality")
    
    # 없으면 필요
    if not llm_judge_quality:
        return True
    
    # 에러가 있으면 필요
    if llm_judge_quality.get("error", False):
        return True
    
    # 모든 점수가 0이면 필요 (평가 실패로 간주)
    scores = [
        llm_judge_quality.get("completeness", 0),
        llm_judge_quality.get("information_richness", 0),
        llm_judge_quality.get("factual_accuracy", 0),
        llm_judge_quality.get("coherence", 0),
        llm_judge_quality.get("helpfulness", 0),
        llm_judge_quality.get("overall_score", 0),
    ]
    
    if all(s == 0 for s in scores):
        return True
    
    return False


def add_llm_judge_to_results(
    results: List[Dict[str, Any]],
    queries_data: List[Dict[str, Any]],
    answer_quality_evaluator: AnswerQualityEvaluator,
    force_recalculate: bool = False
) -> List[Dict[str, Any]]:
    """결과에 LLM Judge 평가 추가"""
    
    # query를 빠르게 찾기 위한 dict
    query_map = {q["query"]: q for q in queries_data}
    
    updated_results = []
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, result in enumerate(results):
        # LLM Judge가 필요 없는 경우
        if not force_recalculate and not needs_llm_judge(result):
            updated_results.append(result)
            skipped_count += 1
            continue
        
        query = result.get("query", "")
        state_output = result.get("state_output", {})
        final_answer = state_output.get("final_answer", "")
        
        # 해당 쿼리 정보 찾기
        query_data = query_map.get(query, {})
        query_type = query_data.get("query_type", result.get("query_type", "factual"))
        
        print(f"  [{idx+1}/{len(results)}] {query[:60]}...")
        
        if not final_answer:
            print(f"    ⚠ 답변 없음, 스킵")
            result["llm_judge_quality"] = {
                "completeness": 0,
                "information_richness": 0,
                "factual_accuracy": 0,
                "coherence": 0,
                "helpfulness": 0,
                "overall_score": 0,
                "reasoning": "답변 없음",
                "error": True
            }
            updated_results.append(result)
            error_count += 1
            continue
        
        try:
            # LLM Judge 평가 실행
            llm_judge_quality = answer_quality_evaluator.evaluate(
                query=query,
                query_type=query_type,
                answer=final_answer
            )
            
            # 결과 업데이트
            result["llm_judge_quality"] = llm_judge_quality
            
            overall_score = llm_judge_quality.get("overall_score", 0)
            print(f"    ✓ LLM Judge: {overall_score:.4f}")
            
            updated_count += 1
            
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:100]}")
            result["llm_judge_quality"] = {
                "completeness": 0,
                "information_richness": 0,
                "factual_accuracy": 0,
                "coherence": 0,
                "helpfulness": 0,
                "overall_score": 0,
                "reasoning": f"평가 실패: {str(e)}",
                "error": True
            }
            error_count += 1
        
        updated_results.append(result)
    
    print(f"\n{'='*70}")
    print(f"처리 완료:")
    print(f"  업데이트: {updated_count}개")
    print(f"  스킵: {skipped_count}개")
    print(f"  에러: {error_count}개")
    print(f"{'='*70}")
    
    return updated_results


def main():
    parser = argparse.ArgumentParser(description="기존 batch 결과에 LLM Judge 평가 추가")
    parser.add_argument("--input-file", type=str, required=True,
                        help="입력 JSON 파일 경로")
    parser.add_argument("--output-file", type=str, default=None,
                        help="출력 JSON 파일 경로 (기본: 입력 파일과 동일)")
    parser.add_argument("--queries", type=str,
                        default="backend/ragas/ontology_evaluate/data/test_queries.json",
                        help="질문 파일 경로")
    parser.add_argument("--force", action="store_true",
                        help="이미 평가된 항목도 강제로 재평가")
    
    args = parser.parse_args()
    
    input_file = Path(args.input_file)
    output_file = Path(args.output_file) if args.output_file else input_file
    
    print("=" * 80)
    print(f"LLM Judge 평가 추가")
    print("=" * 80)
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print(f"강제 재평가: {args.force}")
    
    # 1. 결과 파일 로드
    print(f"\n📂 결과 파일 로드 중...")
    with open(input_file, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    print(f"  ✓ 전체 결과: {len(results)}개")
    
    # 2. 질문 데이터 로드
    queries_data = load_queries(args.queries)
    print(f"  ✓ 질문 데이터: {len(queries_data)}개")
    
    # 3. 평가자 초기화
    print("\n🔧 평가자 초기화 중...")
    answer_quality_evaluator = AnswerQualityEvaluator()
    print("  ✓ 초기화 완료")
    
    # 4. LLM Judge 평가 추가
    start_time = time.time()
    
    updated_results = add_llm_judge_to_results(
        results,
        queries_data,
        answer_quality_evaluator,
        force_recalculate=args.force
    )
    
    elapsed = time.time() - start_time
    
    # 5. 결과 저장
    print(f"\n💾 결과 저장 중...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated_results, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 저장 완료: {output_file}")
    
    print(f"\n{'='*70}")
    print(f"✅ 완료!")
    print(f"{'='*70}")
    print(f"  처리 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    if updated_results:
        avg_time = elapsed / len(updated_results)
        print(f"  평균 시간: {avg_time:.2f}초/개")
    
    # 통계
    judge_scores = [
        r["llm_judge_quality"].get("overall_score", 0)
        for r in updated_results
        if r.get("llm_judge_quality") and not r["llm_judge_quality"].get("error", False)
    ]
    
    if judge_scores:
        avg_score = sum(judge_scores) / len(judge_scores)
        print(f"\n  LLM Judge 평균 점수: {avg_score:.4f} ({len(judge_scores)}개)")


if __name__ == "__main__":
    main()




