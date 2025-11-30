"""
LangGraph 통합 테스트 스크립트

이 스크립트는 다음을 테스트합니다:
1. Fuseki 연결 테스트
2. 더미 데이터 Fuseki 삽입
3. What-if 질문으로 트리플 생성 테스트
4. SPARQL 생성 테스트
5. 전체 그래프 엔드투엔드 테스트
"""

import os
import sys
import time
import requests
from pathlib import Path
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

# LangSmith 프로젝트 이름 변경 (랭그래프 전용)
os.environ["LANGCHAIN_PROJECT"] = "Korean-History-LangGraph"

# 경로 설정
PROJECT_ROOT = Path(__file__).parent
DUMMY_DATA_PATH = PROJECT_ROOT / "ontology" / "instances" / "korean_history_instances.ttl 01-42-57-943.ttl"
FUSEKI_URL = "http://localhost:3030"
INFERENCE_API_URL = "http://localhost:8001"

# Fuseki 인증 정보
FUSEKI_USER = os.getenv("FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.getenv("FUSEKI_PASSWORD", "fuseki1234")
FUSEKI_AUTH = (FUSEKI_USER, FUSEKI_PASSWORD)

# 색상 출력
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test_header(title):
    """테스트 헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")

def print_success(message):
    """성공 메시지"""
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    """에러 메시지"""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_info(message):
    """정보 메시지"""
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.ENDC}")


# =================================================================
# 테스트 1: Fuseki 연결 테스트
# =================================================================

def test_fuseki_connection():
    """Fuseki 서버 연결 테스트"""
    print_test_header("테스트 1: Fuseki 연결 테스트")

    try:
        # Fuseki 서버 상태 확인 (ping은 인증 불필요)
        response = requests.get(f"{FUSEKI_URL}/$/ping", timeout=5)

        if response.status_code == 200:
            print_success("Fuseki 서버 실행 중")
        else:
            print_error(f"Fuseki 서버 응답 코드: {response.status_code}")
            return False

        # 데이터셋 목록 확인 (인증 필요)
        response = requests.get(f"{FUSEKI_URL}/$/datasets", auth=FUSEKI_AUTH, timeout=5)
        if response.status_code == 200:
            datasets = response.json()
            print_success(f"데이터셋 목록 조회 성공")
            print_info(f"사용 가능한 데이터셋: {datasets}")
            return True
        else:
            print_error("데이터셋 목록 조회 실패")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Fuseki 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        print_info("실행 명령: docker-compose up -d fuseki 또는 수동 실행")
        return False
    except Exception as e:
        print_error(f"예상치 못한 오류: {e}")
        return False


# =================================================================
# 테스트 2: 더미 데이터 Fuseki 삽입
# =================================================================

def test_load_dummy_data():
    """더미 데이터를 Fuseki에 업로드"""
    print_test_header("테스트 2: 더미 데이터 Fuseki 업로드")

    # 데이터셋 이름
    dataset_name = "korean_history_test"

    # 1. 더미 데이터 파일 확인
    if not DUMMY_DATA_PATH.exists():
        print_error(f"더미 데이터 파일을 찾을 수 없습니다: {DUMMY_DATA_PATH}")
        return False

    print_success(f"더미 데이터 파일 확인: {DUMMY_DATA_PATH.name}")

    # 2. 파일 크기 확인
    file_size_mb = DUMMY_DATA_PATH.stat().st_size / (1024 * 1024)
    print_info(f"파일 크기: {file_size_mb:.2f} MB")

    # 3. 데이터셋 생성 (이미 존재하면 건너뜀)
    try:
        create_dataset_url = f"{FUSEKI_URL}/$/datasets"
        payload = {
            "dbName": dataset_name,
            "dbType": "tdb2"
        }

        response = requests.post(create_dataset_url, data=payload, auth=FUSEKI_AUTH, timeout=10)

        if response.status_code == 200:
            print_success(f"데이터셋 '{dataset_name}' 생성 성공")
        elif response.status_code == 409:
            print_info(f"데이터셋 '{dataset_name}'이 이미 존재합니다")
        else:
            print_error(f"데이터셋 생성 실패: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"데이터셋 생성 중 오류: {e}")
        return False

    # 4. 데이터 업로드
    try:
        upload_url = f"{FUSEKI_URL}/{dataset_name}/data"

        # 파일이 너무 크면 경고
        if file_size_mb > 100:
            print_info(f"파일이 큽니다 ({file_size_mb:.2f} MB). 업로드에 시간이 걸릴 수 있습니다...")

        with open(DUMMY_DATA_PATH, 'rb') as f:
            headers = {'Content-Type': 'text/turtle'}
            response = requests.post(upload_url, data=f, headers=headers, auth=FUSEKI_AUTH, timeout=300)

        if response.status_code == 200 or response.status_code == 201:
            print_success("더미 데이터 업로드 성공")
        else:
            print_error(f"데이터 업로드 실패: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.Timeout:
        print_error("업로드 시간 초과 (5분)")
        return False
    except Exception as e:
        print_error(f"데이터 업로드 중 오류: {e}")
        return False

    # 5. 업로드 확인 (SPARQL 쿼리)
    try:
        sparql_url = f"{FUSEKI_URL}/{dataset_name}/query"
        sparql = SPARQLWrapper(sparql_url)
        sparql.setReturnFormat(JSON)
        sparql.setQuery("""
            SELECT (COUNT(*) as ?count) WHERE {
                ?s ?p ?o
            }
        """)

        results = sparql.query().convert()
        count = int(results['results']['bindings'][0]['count']['value'])

        print_success(f"트리플 개수: {count:,}개")

        if count > 0:
            return True
        else:
            print_error("업로드된 트리플이 없습니다")
            return False

    except Exception as e:
        print_error(f"데이터 확인 중 오류: {e}")
        return False


# =================================================================
# 테스트 3: Jena Reasoner API 연결 테스트
# =================================================================

def test_inference_api_connection():
    """Jena Reasoner API 서버 연결 테스트"""
    print_test_header("테스트 3: Jena Reasoner API 연결 테스트")

    try:
        response = requests.get(f"{INFERENCE_API_URL}/health", timeout=5)

        if response.status_code == 200:
            health_data = response.json()
            print_success("Inference API 서버 실행 중")
            print_info(f"상태: {health_data}")

            if health_data.get("reasoner_jar_exists"):
                print_success("Reasoner JAR 파일 확인됨")
                return True
            else:
                print_error("Reasoner JAR 파일을 찾을 수 없습니다")
                print_info(f"경로: {health_data.get('jar_path')}")
                return False
        else:
            print_error(f"API 서버 응답 오류: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Inference API 서버에 연결할 수 없습니다")
        print_info("실행 명령: python ontology/scripts/realtime_inference_api.py")
        return False
    except Exception as e:
        print_error(f"예상치 못한 오류: {e}")
        return False


# =================================================================
# 테스트 4: What-if 트리플 생성 테스트
# =================================================================

def test_hypothetical_triple_generation():
    """What-if 질문으로 가상 트리플 생성 테스트"""
    print_test_header("테스트 4: What-if 트리플 생성 테스트")

    from nodes.kg.hypothetical_triple_node import hypothetical_triple_node
    from state import GraphState

    # 테스트 케이스
    test_cases = [
        {
            "query": "만약 이순신이 명량해전에서 패배했다면?",
            "entities": [
                {"name": "이순신", "type": "Person"},
                {"name": "명량해전", "type": "Battle"}
            ]
        },
        {
            "query": "만약 세종대왕이 한글을 창제하지 않았다면?",
            "entities": [
                {"name": "세종대왕", "type": "Person"},
                {"name": "한글", "type": "WritingSystem"}
            ]
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n테스트 케이스 {i}: {test_case['query']}")

        state: GraphState = {
            "query": test_case["query"],
            "query_type": "what_if",
            "extracted_entities": test_case["entities"]
        }

        try:
            result_state = hypothetical_triple_node(state)
            triples = result_state.get("hypothetical_triples", [])

            if triples:
                print_success(f"{len(triples)}개의 가상 트리플 생성됨:")
                for triple in triples:
                    print(f"   {triple}")
            else:
                print_error("트리플이 생성되지 않았습니다")

        except Exception as e:
            print_error(f"트리플 생성 실패: {e}")
            return False

    return True


# =================================================================
# 테스트 5: SPARQL 생성 테스트
# =================================================================

def test_sparql_generation():
    """LLM 기반 SPARQL 쿼리 생성 테스트"""
    print_test_header("테스트 5: SPARQL 쿼리 생성 테스트")

    from nodes.multi_query_generator_node import multi_query_generator_node
    from state import GraphState

    # 테스트 질문
    state: GraphState = {
        "query": "이순신이 명량해전에서 왜 승리했을까?",
        "query_type": "causal",
        "extracted_entities": [
            {"name": "이순신", "type": "Person", "uri": "hist:YiSunSin"},
            {"name": "명량해전", "type": "Battle", "uri": "hist:Myeongnyang"}
        ]
    }

    try:
        result_state = multi_query_generator_node(state)
        multi_queries = result_state.get("multi_queries", {})

        if multi_queries:
            print_success(f"{len(multi_queries)}개의 SPARQL 쿼리 생성됨\n")

            for thread_type, sparql in multi_queries.items():
                print(f"{Colors.BOLD}[{thread_type}]{Colors.ENDC}")
                print(f"{sparql}\n")

            return True
        else:
            print_error("SPARQL 쿼리가 생성되지 않았습니다")
            return False

    except Exception as e:
        print_error(f"SPARQL 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# =================================================================
# 테스트 6: 전체 그래프 엔드투엔드 테스트
# =================================================================

def test_full_graph_execution():
    """전체 LangGraph 실행 테스트"""
    print_test_header("테스트 6: 전체 그래프 엔드투엔드 테스트")

    from graph import graph
    from state import GraphState

    # 테스트 질문
    test_query = "이순신이 명량해전에서 왜 승리했을까?"

    print(f"질문: {test_query}\n")

    # 초기 상태
    initial_state: GraphState = {
        "query": test_query
    }

    try:
        print_info("그래프 실행 시작...\n")
        start_time = time.time()

        # 그래프 실행
        final_state = graph.invoke(initial_state)

        elapsed = time.time() - start_time

        print_success(f"그래프 실행 완료 ({elapsed:.1f}초)\n")

        # 실행된 노드 확인
        executed_nodes = final_state.get("executed_nodes", [])
        print(f"{Colors.BOLD}실행된 노드:{Colors.ENDC}")
        for node in executed_nodes:
            print(f"  ✓ {node}")

        # 결과 확인
        print(f"\n{Colors.BOLD}주요 결과:{Colors.ENDC}")
        print(f"  - 질문 유형: {final_state.get('query_type', 'N/A')}")
        print(f"  - 추출된 엔티티: {len(final_state.get('extracted_entities', []))}개")
        print(f"  - 생성된 쿼리: {len(final_state.get('multi_queries', {}))}개")
        print(f"  - 추론 결과: {len(final_state.get('parallel_inference_results', {}))}개")
        print(f"  - 추출된 근거: {len(final_state.get('evidences', []))}개")

        # 최종 답변 출력
        final_answer = final_state.get("final_answer")
        if final_answer:
            print(f"\n{Colors.BOLD}최종 답변:{Colors.ENDC}")
            print(final_answer)
            print_success("\n전체 그래프 테스트 성공")
            return True
        else:
            print_error("최종 답변이 생성되지 않았습니다")
            return False

    except Exception as e:
        print_error(f"그래프 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# =================================================================
# 메인 실행
# =================================================================

def main():
    """모든 테스트 실행"""

    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     LangGraph 온톨로지 추론 시스템 통합 테스트          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")

    results = {}

    # 테스트 1: Fuseki 연결
    results["Fuseki 연결"] = test_fuseki_connection()

    if not results["Fuseki 연결"]:
        print_error("\nFuseki 서버가 실행되지 않아 테스트를 중단합니다")
        print_info("다음 명령으로 Fuseki를 시작하세요:")
        print_info("  docker-compose up -d fuseki")
        return

    # 테스트 2: 더미 데이터 업로드
    results["더미 데이터 업로드"] = test_load_dummy_data()

    # 테스트 3: Inference API 연결
    results["Inference API 연결"] = test_inference_api_connection()

    if not results["Inference API 연결"]:
        print_info("\nInference API가 필요한 테스트를 건너뜁니다")
        print_info("API 서버 시작 명령:")
        print_info("  cd ontology/scripts && python realtime_inference_api.py")

    # 테스트 4: What-if 트리플 생성
    results["What-if 트리플 생성"] = test_hypothetical_triple_generation()

    # 테스트 5: SPARQL 생성
    results["SPARQL 생성"] = test_sparql_generation()

    # 테스트 6: 전체 그래프 (Inference API 필요)
    if results["Inference API 연결"]:
        results["전체 그래프 실행"] = test_full_graph_execution()
    else:
        results["전체 그래프 실행"] = None

    # 결과 요약
    print_test_header("테스트 결과 요약")

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results.items():
        if result is True:
            print_success(f"{test_name}")
            passed += 1
        elif result is False:
            print_error(f"{test_name}")
            failed += 1
        else:
            print_info(f"{test_name} (건너뜀)")
            skipped += 1

    print(f"\n{Colors.BOLD}총 {len(results)}개 테스트{Colors.ENDC}")
    print(f"  ✅ 성공: {passed}")
    print(f"  ❌ 실패: {failed}")
    print(f"  ⏭️  건너뜀: {skipped}\n")

    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 모든 테스트 통과!{Colors.ENDC}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  일부 테스트 실패{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
