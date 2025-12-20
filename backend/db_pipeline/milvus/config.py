import os
from dotenv import load_dotenv
load_dotenv(override=True)

milvus_config = {
    "host": os.getenv("MILVUS_HOST", "localhost"),
    "port": os.getenv("MILVUS_PORT", "19530"),
    "user": os.getenv("MILVUS_USERNAME", "root"),
    "password": os.getenv("MILVUS_PASSWORD", "mysecurepassword"),
    "alias": os.getenv("MILVUS_ALIAS", "milvus_dev"),
    "collection_name": os.getenv("MILVUS_COLLECTION_NAME", "document_embeddings")
}
