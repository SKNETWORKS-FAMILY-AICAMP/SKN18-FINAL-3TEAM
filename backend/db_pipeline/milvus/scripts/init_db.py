from db.connection import connect_milvus
from db.collection import create_collection, get_collection
from db.vector_index import create_index
from config import milvus_config

# 연결
connect_milvus(milvus_config)

# 컬렉션 삭제(이미 존재할 경우 대비)
# 존재 유무 먼저 확인
collection = get_collection(milvus_config["collection_name"], milvus_config["alias"])
if collection:
    collection.drop()
    print("컬렉션 삭제 완료")

# 컬렉션 생성
collection = create_collection(milvus_config["collection_name"], milvus_config["alias"])
print(f"컬렉션 '{collection.name}' 생성 완료")

# 벡터 인덱스 생성
create_index(collection)