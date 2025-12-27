"""
Baseline Ablation Study: Phase 1 실험

각 요소(Semantic Expander, Thread)를 비활성화하여 기여도 측정
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import time
from pathlib import Path


@dataclass
class AblationConfig:
    """Ablation 실험 설정"""

    # Semantic Expander 비활성화 설정
    semantic_expander: Dict[str, bool] = None  # {"temporal": True, "causal_chain": False, "pgvector": True}

    # Thread 비활성화 설정
    aggregator_threads: Dict[str, bool] = None  # {"outgoing_relations": True, ...}

    # Entity Boost 모드
    entity_boost_mode: Optional[str] = None  # "exact_match" | "partial_match" | ...

    # 실험 이름
    experiment_name: str = "baseline"

    # 설명
    description: str = ""

    def __post_init__(self):
        if self.semantic_expander is None:
            self.semantic_expander = {
                "temporal": True,
                "causal_chain": True,
                "pgvector": True
            }

        if self.aggregator_threads is None:
            self.aggregator_threads = {
                "outgoing_relations": True,
                "incoming_relations": True,
                "entity_properties": True,
                "connected_entities": True,
                "type_and_summary": True
            }

    def to_state_config(self) -> Dict[str, Any]:
        """GraphState의 test_config 형식으로 변환"""
        return {
            "semantic_expander": self.semantic_expander,
            "aggregator_threads": self.aggregator_threads,
            "entity_boost_mode": self.entity_boost_mode
        }


class AblationExperimentGenerator:
    """Ablation 실험 설정 생성기"""

    @staticmethod
    def generate_semantic_expander_experiments() -> List[AblationConfig]:
        """Semantic Expander Ablation 실험 생성

        Returns:
            실험 설정 리스트 (5개):
            1. Baseline: 모든 확장 비활성화
            2. Temporal Only
            3. Causal Chain Only
            4. Pgvector Only
            5. All Enabled (Full)
        """
        experiments = []

        # 1. Baseline: 모든 확장 비활성화
        experiments.append(AblationConfig(
            semantic_expander={
                "temporal": False,
                "causal_chain": False,
                "pgvector": False
            },
            experiment_name="semantic_expander_baseline",
            description="모든 Semantic Expander 비활성화 (Entity Extractor 30개만 사용)"
        ))

        # 2-4. 각 확장 방법 개별 활성화
        expansion_methods = ["temporal", "causal_chain", "pgvector"]
        for method in expansion_methods:
            config = {
                "temporal": False,
                "causal_chain": False,
                "pgvector": False
            }
            config[method] = True

            experiments.append(AblationConfig(
                semantic_expander=config,
                experiment_name=f"semantic_expander_{method}_only",
                description=f"{method} 확장만 활성화"
            ))

        # 5. All Enabled (Full)
        experiments.append(AblationConfig(
            semantic_expander={
                "temporal": True,
                "causal_chain": True,
                "pgvector": True
            },
            experiment_name="semantic_expander_full",
            description="모든 Semantic Expander 활성화 (기본 설정)"
        ))

        return experiments

    @staticmethod
    def generate_thread_experiments() -> List[AblationConfig]:
        """Thread Ablation 실험 생성 (Leave-One-Out)

        Returns:
            실험 설정 리스트 (6개):
            1. Baseline: 1개 Thread만 (outgoing_relations)
            2-6. 각 Thread 하나씩 제거
        """
        experiments = []

        # 1. Baseline: 1개 Thread만
        experiments.append(AblationConfig(
            aggregator_threads={
                "outgoing_relations": True,
                "incoming_relations": False,
                "entity_properties": False,
                "connected_entities": False,
                "type_and_summary": False
            },
            experiment_name="thread_baseline",
            description="outgoing_relations Thread만 활성화"
        ))

        # 2-6. Leave-One-Out (각 Thread 하나씩 제거)
        thread_names = [
            "outgoing_relations",
            "incoming_relations",
            "entity_properties",
            "connected_entities",
            "type_and_summary"
        ]

        for excluded_thread in thread_names:
            config = {thread: True for thread in thread_names}
            config[excluded_thread] = False

            experiments.append(AblationConfig(
                aggregator_threads=config,
                experiment_name=f"thread_without_{excluded_thread}",
                description=f"{excluded_thread} Thread 제거 (나머지 4개 활성화)"
            ))

        return experiments

    @staticmethod
    def generate_entity_boost_experiments() -> List[AblationConfig]:
        """Entity Boost Mode 실험 생성

        Returns:
            실험 설정 리스트 (4개):
            1. exact_match (1.5배)
            2. partial_match (1.3배)
            3. normalized_match (1.2배)
            4. penalty_match (0.8배)
        """
        experiments = []

        boost_modes = ["exact_match", "partial_match", "normalized_match", "penalty_match"]
        for mode in boost_modes:
            experiments.append(AblationConfig(
                entity_boost_mode=mode,
                experiment_name=f"entity_boost_{mode}",
                description=f"Entity Boost Mode: {mode}"
            ))

        return experiments

    @staticmethod
    def generate_all_experiments() -> Dict[str, List[AblationConfig]]:
        """모든 Ablation 실험 생성

        Returns:
            실험 그룹별 설정 딕셔너리:
            {
                "semantic_expander": [6개 실험],
                "thread": [6개 실험],
                "entity_boost": [4개 실험]
            }
        """
        return {
            "semantic_expander": AblationExperimentGenerator.generate_semantic_expander_experiments(),
            "thread": AblationExperimentGenerator.generate_thread_experiments(),
            "entity_boost": AblationExperimentGenerator.generate_entity_boost_experiments()
        }


class AblationRunner:
    """Ablation 실험 실행기"""

    def __init__(self, output_dir: str = "data/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 로그 디렉토리 생성
        self.log_dir = Path("backend/ragas/ontology_evaluate/log")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def clean_state_output(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        state_output에서 불필요한 대용량 데이터 제거
        
        제거 대상:
        - ontology_schema: 온톨로지 스키마 (매번 동일)
        - ttl_data: TTL 데이터 (매번 동일)
        """
        if not isinstance(state_output, dict):
            return state_output
        
        cleaned = state_output.copy()
        
        # 제거할 키 목록
        keys_to_remove = ["ontology_schema", "ttl_data", "raw_ttl_content", "full_schema", "metadata_cache"]
        
        for key in keys_to_remove:
            if key in cleaned:
                del cleaned[key]
        
        return cleaned

    def run_single_experiment(
        self,
        query: str,
        config: AblationConfig,
        graph_invoke_func
    ) -> Dict[str, Any]:
        """단일 실험 실행

        Args:
            query: 테스트 질문
            config: Ablation 설정
            graph_invoke_func: LangGraph invoke 함수

        Returns:
            실험 결과 딕셔너리:
            {
                "experiment_name": str,
                "query": str,
                "config": dict,
                "state_output": dict,
                "execution_time": float,
                "metrics": dict  # 평가 메트릭 (evaluators에서 계산)
            }
        """
        print(f"\n{'='*70}")
        print(f"실험: {config.experiment_name}")
        print(f"설명: {config.description}")
        print(f"질문: {query}")
        print(f"{'='*70}")

        start_time = time.time()

        # GraphState에 test_config 주입
        initial_state = {
            "query": query,
            "test_config": config.to_state_config()
        }

        # LangGraph 실행
        try:
            state_output = graph_invoke_func(initial_state)
            success = True
            error = None
        except Exception as e:
            state_output = {}
            success = False
            error = str(e)

        execution_time = time.time() - start_time

        result = {
            "experiment_name": config.experiment_name,
            "description": config.description,
            "query": query,
            "config": config.to_state_config(),
            "state_output": self.clean_state_output(state_output),  # 불필요한 데이터 제거
            "execution_time": execution_time,
            "success": success,
            "error": error,
            "metrics": {}  # 평가 메트릭은 별도로 계산
        }

        print(f"  ├─ 실행 시간: {execution_time:.2f}초")
        print(f"  ├─ 성공: {success}")
        if not success:
            print(f"  └─ 에러: {error}")

        return result

    def run_experiment_group(
        self,
        queries: List[str],
        configs: List[AblationConfig],
        graph_invoke_func,
        group_name: str
    ) -> List[Dict[str, Any]]:
        """실험 그룹 실행 (여러 질문 × 여러 설정)

        Args:
            queries: 테스트 질문 리스트
            configs: Ablation 설정 리스트
            graph_invoke_func: LangGraph invoke 함수
            group_name: 실험 그룹 이름 (예: "semantic_expander")

        Returns:
            실험 결과 리스트
        """
        import logging
        import datetime
        
        # 로그 설정
        log_file = self.log_dir / f"{group_name}_experiment.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='w'
        )
        logger = logging.getLogger()
        
        results = []

        total_experiments = len(queries) * len(configs)
        print(f"\n{'='*70}")
        print(f"실험 그룹: {group_name}")
        print(f"총 {total_experiments}개 실험 (질문 {len(queries)}개 × 설정 {len(configs)}개)")
        print(f"{'='*70}")
        
        logger.info(f"실험 그룹 시작: {group_name}")
        logger.info(f"총 {total_experiments}개 실험 (질문 {len(queries)}개 × 설정 {len(configs)}개)")

        for i, query in enumerate(queries, 1):
            for j, config in enumerate(configs, 1):
                print(f"\n진행률: [{i}/{len(queries)}] 질문, [{j}/{len(configs)}] 설정")
                logger.info(f"진행률: [{i}/{len(queries)}] 질문, [{j}/{len(configs)}] 설정")

                result = self.run_single_experiment(query, config, graph_invoke_func)
                results.append(result)
                
                # 매 5개 실험마다 임시 저장 (append 방식)
                if len(results) % 5 == 0:
                    temp_file = self.output_dir / f"{group_name}_temp.json"

                    # 기존 temp 파일이 있으면 읽어서 병합
                    existing_temp = []
                    if temp_file.exists():
                        with open(temp_file, "r", encoding="utf-8") as f:
                            existing_temp = json.load(f)

                    # 기존 결과 + 이번 실행 결과 병합
                    merged_temp = existing_temp + results

                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(merged_temp, f, ensure_ascii=False, indent=2)
                    print(f"  ├─ 임시 저장: {temp_file} ({len(merged_temp)}개 실험)")
                    logger.info(f"임시 저장: {temp_file} ({len(merged_temp)}개 실험)")

        # 최종 결과 저장
        output_file = self.output_dir / f"{group_name}_ablation.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n  └─ 결과 저장: {output_file}")
        logger.info(f"최종 결과 저장: {output_file}")
        
        # 임시 파일 삭제
        temp_file = self.output_dir / f"{group_name}_temp.json"
        if temp_file.exists():
            temp_file.unlink()
            logger.info(f"임시 파일 삭제: {temp_file}")
        
        return results

    def run_all_experiments(
        self,
        queries: List[str],
        graph_invoke_func
    ) -> Dict[str, List[Dict[str, Any]]]:
        """모든 Ablation 실험 실행

        Args:
            queries: 테스트 질문 리스트
            graph_invoke_func: LangGraph invoke 함수

        Returns:
            그룹별 실험 결과 딕셔너리
        """
        all_experiments = AblationExperimentGenerator.generate_all_experiments()
        all_results = {}

        for group_name, configs in all_experiments.items():
            results = self.run_experiment_group(
                queries=queries,
                configs=configs,
                graph_invoke_func=graph_invoke_func,
                group_name=group_name
            )
            all_results[group_name] = results

        return all_results


# 사용 예시 (main에서 실행)
if __name__ == "__main__":
    # 예시: 실험 설정 생성
    experiments = AblationExperimentGenerator.generate_all_experiments()

    print("생성된 실험 그룹:")
    for group_name, configs in experiments.items():
        print(f"\n{group_name}: {len(configs)}개 실험")
        for config in configs:
            print(f"  - {config.experiment_name}: {config.description}")

    # 실험 실행은 experiments/run_baseline.py에서 수행
