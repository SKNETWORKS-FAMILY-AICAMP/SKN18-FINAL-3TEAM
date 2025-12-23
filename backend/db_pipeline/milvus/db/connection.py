from pymilvus import connections

def connect_milvus(milvus_config):
    # 인증을 사용한 Milvus 접속
    connections.connect(
        alias=milvus_config["alias"],           # 연결 이름, 여러 Milvus 서버를 사용할 때 구분 가능
        host=milvus_config["host"],          # Milvus 서버 주소 (Docker에서 localhost)
        port=milvus_config["port"],              # Milvus gRPC 포트
        user=milvus_config["user"],               # 인증 활성화 시 Milvus 관리자 계정
        password=milvus_config["password"] # 인증 활성화 시 Milvus 비밀번호
    )

    print("Milvus 연결 성공!")