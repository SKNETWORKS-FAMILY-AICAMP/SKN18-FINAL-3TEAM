from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd

CHUNK = 5000
OVERLAP = 300
MAX_LEN = 65000
BATCH = 200

def splitter_chunks():
    loader = TextLoader("./backend/db_pipeline/data/encykorea_cleaned6.csv", encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK,
        chunk_overlap=OVERLAP,
        length_function=len,
        is_separator_regex=False,
        separators=[
            "\n\n", "\n",
            r"(?<=[.?!])\s+",
            r"(?<=[다요죠음함임니다])[\.\?!]?\s+",
            " ", "",
        ],
    )
    docs_with_splitter = splitter.split_documents(docs)

    trimmed_docs = []
    for d in docs_with_splitter:
        title = d.metadata.get("title", "") if d.metadata else ""
        summary = d.metadata.get("summary", "") if d.metadata else ""
        allowed = MAX_LEN - len(title) - len(summary)
        content = d.page_content
        if allowed > 0 and len(content) > allowed:
            content = content[:allowed]
        d.page_content = content
        trimmed_docs.append(d)

    return trimmed_docs, BATCH


# import pandas as pd
# from langchain.schema import Document
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# CHUNK = 5000
# OVERLAP = 300
# MAX_LEN = 65000
# BATCH = 200

# def prepare_chunks():
#     df = pd.read_csv("backend/db_pipeline/data/encykorea_cleaned6.csv").fillna("")
#     docs = [
#         Document(
#             page_content=row["contents"],
#             metadata={
#                 "title": row["title"],
#                 "summary": row["summary"],
#                 "category": row["category"],
#             },
#         )
#         for _, row in df.iterrows()
#     ]

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK,
#         chunk_overlap=OVERLAP,
#         length_function=len,
#         is_separator_regex=False,
#         separators=["\n\n", "\n", r"(?<=[.?!])\s+", r"(?<=[다요죠음함임니다])[\.\?!]?\s+", " ", ""],
#     )
#     chunks = splitter.split_documents(docs)

#     trimmed = []
#     for d in chunks:
#         title = d.metadata.get("title", "")
#         summary = d.metadata.get("summary", "")
#         allowed = MAX_LEN - len(title) - len(summary)
#         if allowed > 0 and len(d.page_content) > allowed:
#             d.page_content = d.page_content[:allowed]
#         trimmed.append(d)

#     return trimmed, BATCH
