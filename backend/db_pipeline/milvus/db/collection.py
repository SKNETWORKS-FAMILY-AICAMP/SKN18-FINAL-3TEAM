from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

# 컬렉션 스키마 정의
def create_collection(milvus_collection_name, milvus_alias):
    # 필드 정의 : category, title, summary, contents, embedding
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="contents", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
    ]
    
    # 스키마 생성
    schema = CollectionSchema(fields, "문서 임베딩을 위한 컬렉션")
    
    # 컬렉션 생성
    collection = Collection(name=milvus_collection_name # 컬렉션 이름
                            , schema=schema # 스키마
                            , using=milvus_alias # 위에서 정의한 connections의 alias
    )
    
    return collection

# 기존 컬렉션 가져오기
def get_collection(name: str, alias: str = "default") -> Collection:
    return Collection(name=name, using=alias)