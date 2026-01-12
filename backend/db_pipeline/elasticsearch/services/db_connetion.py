from elasticsearch import Elasticsearch
import warnings
warnings.filterwarnings('ignore')

# Elasticsearch 클라이언트 생성
# elasticsearch 9.x는 명시적인 scheme 지정이 필요합니다

def create_connection():
    try:
        es_client = Elasticsearch(
            ["http://localhost:9200"],  # 리스트 형태로, scheme 포함
            basic_auth=("elastic", "changeme123!"),  # 인증 정보 (보안 활성화 시 필수)
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
            # 호환성 헤더 비활성화 (개발 환경용)
            headers={"accept": "application/json", "content-type": "application/json"}
        )
        
        # 연결 확인
        if es_client.ping():
            print("Elasticsearch 연결 성공!")
            print()
            
            # 클러스터 정보
            info = es_client.info()
            print(f"버전: {info['version']['number']}")
            print(f"클러스터 이름: {info['cluster_name']}")
            print(f"노드 이름: {info['name']}")
            print()
            print(f"Elasticsearch URL: http://localhost:9200")
            return es_client
        else:
            print("Elasticsearch 연결 실패 (ping 실패)")
            
    except Exception as e:
        print("Elasticsearch 연결 중 오류 발생:")
        print(f"   에러 타입: {type(e).__name__}")
        print(f"   에러 메시지: {str(e)}")
