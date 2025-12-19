# 데이터 삽입
from db.ingest_data import insert_data
from db.connection import connect_milvus
from db.collection import get_collection
from config import milvus_config

# 연결
connect_milvus(milvus_config)

# 컬렉션 가져오기
collection = get_collection(
    milvus_config["collection_name"],
    milvus_config["alias"]
)

# 데이터 삽입
insert_data(collection)