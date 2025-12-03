from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv(override=True)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def get_embedding():
    return embeddings