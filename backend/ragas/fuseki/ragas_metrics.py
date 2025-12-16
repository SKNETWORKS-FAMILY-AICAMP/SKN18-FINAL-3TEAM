"""
RAGAS Evaluation Metrics for Fuseki-based RAG

평가 지표 (LLM Judge 기반):
- 검색 단계: Context Relevance (질문과 검색된 context의 의미적 관련성)
- 생성 단계:
  - Response Relevancy (질문 적합성 - 답변이 질문에 잘 답하는지)
  - Faithfulness (근거 충실도 - 답변이 context에 기반하는지, 환각 없음)
  - Response Groundedness (근거 사용도 - 답변이 context를 얼마나 사용하는지)
"""

import importlib
import json
from typing import List, Dict, Any
from pathlib import Path


# =====================================================
# RAGAS Safe Import (neo4j/ragas_eval.py 참고)
# =====================================================
def _import_attr(module_name: str, attr_name: str):
    """모듈에서 속성을 안전하게 import"""
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)
    except Exception:
        return None


def _resolve_metric(module_name: str, candidates: List[str], debug=False):
    """메트릭을 다양한 이름으로 시도하여 로드"""
    mod = importlib.import_module(module_name)
    for name in candidates:
        obj = getattr(mod, name, None)
        if obj is None:
            continue
        if isinstance(obj, type):
            try:
                inst = obj()
                if debug:
                    print(f"[DEBUG] metric resolved: {name}()")
                return inst
            except Exception:
                continue
        if debug:
            print(f"[DEBUG] metric resolved: {name}")
        return obj
    return None


def _resolve_evaluate(debug=False):
    """ragas.evaluate 함수 로드"""
    fn = _import_attr("ragas", "evaluate")
    if fn:
        if debug:
            print("[DEBUG] evaluate resolved: ragas.evaluate")
        return fn
    fn = _import_attr("ragas.evaluation", "evaluate")
    if fn:
        if debug:
            print("[DEBUG] evaluate resolved: ragas.evaluation.evaluate")
        return fn
    raise ImportError("Cannot resolve ragas.evaluate")


# =====================================================
# RAGAS Metrics Loader
# =====================================================
class RagasMetricsLoader:
    """
    RAGAS 메트릭을 로드하는 클래스

    평가 지표:
    - 검색 단계: Context Relevance
    - 생성 단계: Response Relevancy, Faithfulness, Response Groundedness
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.evaluate = None
        self.metrics = {}
        self.SingleTurnSample = None
        self.EvaluationDataset = None

    def load_all(self):
        """모든 메트릭 로드"""
        # evaluate 함수 로드
        self.evaluate = _resolve_evaluate(self.debug)

        # Dataset 클래스 로드
        self.SingleTurnSample = _import_attr("ragas.dataset_schema", "SingleTurnSample")
        self.EvaluationDataset = _import_attr("ragas.dataset_schema", "EvaluationDataset")

        if self.SingleTurnSample is None or self.EvaluationDataset is None:
            raise ImportError(
                "Cannot resolve ragas.dataset_schema.SingleTurnSample / EvaluationDataset"
            )

        # 검색 단계 메트릭
        # 1. Context Relevance (질문과 검색된 context의 의미적 관련성)
        self.metrics["context_relevance"] = _resolve_metric(
            "ragas.metrics",
            ["context_relevance", "ContextRelevance", "context_relevancy", "ContextRelevancy"],
            self.debug
        )

        # 생성 단계 메트릭
        # 2. Response Relevancy (질문 적합성 - answer_relevancy)
        self.metrics["answer_relevancy"] = _resolve_metric(
            "ragas.metrics",
            ["answer_relevancy", "AnswerRelevancy", "response_relevancy", "ResponseRelevancy"],
            self.debug
        )

        # 3. Faithfulness (근거 충실도 - 답변이 context에 기반하는지)
        self.metrics["faithfulness"] = _resolve_metric(
            "ragas.metrics",
            ["faithfulness", "Faithfulness"],
            self.debug
        )

        # 4. Response Groundedness (근거 사용도)
        # answer_correctness 또는 response_groundedness로 대체
        self.metrics["response_groundedness"] = _resolve_metric(
            "ragas.metrics",
            ["response_groundedness", "ResponseGroundedness", "answer_correctness", "AnswerCorrectness"],
            self.debug
        )

        # 필터링: None이 아닌 메트릭만 유지
        self.metrics = {k: v for k, v in self.metrics.items() if v is not None}

        if self.debug:
            print(f"[DEBUG] Loaded metrics: {list(self.metrics.keys())}")

        return self.metrics

    def get_metric_list(self) -> List[Any]:
        """메트릭 리스트 반환 (evaluate 함수에 전달용)"""
        return list(self.metrics.values())

    def get_retrieval_metrics(self) -> List[Any]:
        """검색 단계 메트릭 반환"""
        retrieval_metric_names = ["context_relevance"]
        return [self.metrics[name] for name in retrieval_metric_names if name in self.metrics]

    def get_generation_metrics(self) -> List[Any]:
        """생성 단계 메트릭 반환"""
        generation_metric_names = ["answer_relevancy", "faithfulness", "response_groundedness"]
        return [self.metrics[name] for name in generation_metric_names if name in self.metrics]

    def create_sample(
        self,
        user_input: str,
        response: str,
        retrieved_contexts: List[str],
        reference: str = None
    ):
        """SingleTurnSample 생성"""
        if self.SingleTurnSample is None:
            raise RuntimeError("SingleTurnSample not loaded. Call load_all() first.")

        return self.SingleTurnSample(
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts,
            reference=reference
        )

    def create_dataset(self, samples: List):
        """EvaluationDataset 생성"""
        if self.EvaluationDataset is None:
            raise RuntimeError("EvaluationDataset not loaded. Call load_all() first.")

        return self.EvaluationDataset(samples=samples)


# =====================================================
# Utility Functions
# =====================================================
def ensure_str_contexts(contexts: List[Any]) -> List[str]:
    """
    컨텍스트를 문자열 리스트로 변환

    Args:
        contexts: 컨텍스트 리스트 (str 또는 dict)

    Returns:
        문자열 리스트
    """
    out = []
    for c in contexts or []:
        if isinstance(c, str):
            out.append(c)
        else:
            try:
                out.append(json.dumps(c, ensure_ascii=False))
            except Exception:
                out.append(str(c))
    return out


def extract_contexts_from_evidences(evidences: List[Dict]) -> List[str]:
    """
    근거 리스트에서 컨텍스트 문자열 추출

    Args:
        evidences: path_evidence_aggregator_node의 evidences

    Returns:
        컨텍스트 문자열 리스트
    """
    contexts = []
    for ev in evidences:
        description = ev.get("description", "")
        if description:
            contexts.append(description)
    return contexts


def evaluate_with_ragas(
    loader: RagasMetricsLoader,
    samples: List,
    debug: bool = False
) -> Dict[str, float]:
    """
    RAGAS 평가 실행

    Args:
        loader: RagasMetricsLoader 인스턴스
        samples: SingleTurnSample 리스트
        debug: 디버그 모드

    Returns:
        메트릭별 점수 딕셔너리
    """
    if not samples:
        print("[WARNING] No samples to evaluate")
        return {}

    dataset = loader.create_dataset(samples)
    metrics = loader.get_metric_list()

    if not metrics:
        print("[WARNING] No metrics loaded")
        return {}

    if debug:
        print(f"[DEBUG] Evaluating {len(samples)} samples with {len(metrics)} metrics")

    result = loader.evaluate(dataset=dataset, metrics=metrics)

    # pandas DataFrame으로 변환
    df = result.to_pandas()

    # 평균 점수 계산
    scores = {}
    for col in df.columns:
        if col not in ["user_input", "response", "retrieved_contexts", "reference"]:
            scores[col] = df[col].mean()

    return scores


if __name__ == "__main__":
    # 테스트 코드
    print("Testing RagasMetricsLoader...")

    loader = RagasMetricsLoader(debug=True)
    loader.load_all()

    print(f"\nLoaded metrics: {list(loader.metrics.keys())}")

    # 샘플 데이터 생성
    sample = loader.create_sample(
        user_input="세조는 누구였나요?",
        response="세조는 조선의 제7대 왕입니다.",
        retrieved_contexts=[
            "세조는 조선의 제7대 왕이다.",
            "세조는 1455년에 즉위했다.",
            "세조는 수양대군이었다."
        ]
    )

    print(f"\nCreated sample: {sample}")
    print("\nRagasMetricsLoader test completed successfully!")
