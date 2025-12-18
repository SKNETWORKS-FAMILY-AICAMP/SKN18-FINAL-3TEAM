# 벡터 인덱스 생성
def create_index(collection):
    # IVF_FLAT 인덱스 생성 (정확한 검색을 위한 기본 인덱스)
    index_params = {
        "metric_type": "L2",  # 유클리드 거리
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    
    # 임베딩 필드에 인덱스 생성
    collection.create_index("embedding", index_params)
    print("인덱스 생성 완료")
    