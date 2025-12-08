# backend/db_pipeline/ETL/test_pg_search.py

import time
import numpy as np
import openai
from embedding import embedding_model
from create_pgvector import create_pgvector_store

CONNECTION_STRING = "postgresql://admin:admin123@localhost:5432/vectordb"
TABLE = "encykorea_cleaned6"   # 적재된 테이블 이름
TOP_K = 5
COS_THRESHOLD = 0.60

def search(store, query: str, top_k: int = TOP_K):
    """PGVector에서 유사도 검색 + 쿼리/문서 코사인 계산"""
    emb = embedding_model()
    query_vec = emb.embed_query(query)                     # 1) 쿼리 임베딩
    t0 = time.perf_counter()
    results = store.similarity_search_with_score(query, k=top_k)  # 2) 검색
    elapsed = time.perf_counter() - t0

    # 상위 결과들의 임베딩을 다시 계산해 코사인 유사도(질문-문서) 산출
    doc_texts = [doc.page_content for doc, _ in results]
    doc_embs = emb.embed_documents(doc_texts) if doc_texts else []

    doc_infos = []
    for (doc, score), dvec in zip(results, doc_embs):
        vq = np.array(query_vec)
        vd = np.array(dvec)
        cos = float(np.dot(vq, vd) / (np.linalg.norm(vq) * np.linalg.norm(vd)))
        doc_infos.append({
            "cosine_sim": cos,
            "distance": float(score),   # PG vector <-> 결과 (작을수록 유사)
            "meta": doc.metadata,
            "text": doc.page_content,
        })

    return elapsed, doc_infos

def main():
    print("PGVector 스토어 연결 중...")
    store = create_pgvector_store(CONNECTION_STRING, TABLE, embedding_model())

    query = "조선시대 궁궐은 어떻게 생겼나?"
    print(f"\n검색 쿼리: {query}")

    elapsed, doc_infos = search(store, query, top_k=TOP_K)
    print(f"\n검색 완료. 걸린 시간: {elapsed:.4f}초")
    print("-" * 50)

    print("\n[검색 결과별 코사인 유사도]")
    for i, info in enumerate(doc_infos, 1):
        meta = info["meta"] or {}
        print(f"문서 {i}:")
        print(f"  PG distance (L2): {info['distance']:.4f}")
        print(f"  Cosine Sim (Q vs Doc): {info['cosine_sim']:.4f}")
        print(f"  meta: {meta}")
        print(f"  text: {info['text'][:200]}")
        print("-" * 30)


    relevant = [d for d in doc_infos if d["cosine_sim"] >= COS_THRESHOLD]
    docs_for_prompt = relevant if relevant else doc_infos
    if not docs_for_prompt:
        print("\n[INFO] 검색 결과가 없습니다.")
        return

    # 프롬프트용 텍스트
    docs_text = "\n\n".join(
        [
            f"[문서 {i+1}]\n"
            f"(cosine_sim={d['cosine_sim']:.4f}, distance={d['distance']:.4f})\n"
            f"meta: {d['meta']}\n"
            f"text: {d['text'][:300]}"
            for i, d in enumerate(docs_for_prompt)
        ]
    )

    client = openai.OpenAI()

    gen_prompt = f"""
        너는 역사 전문 RAG 기반 답변 생성기이다.
        아래에는 사용자의 질문과 벡터 검색으로 찾은 문서들(근거)이 포함된다.
        [질문]
        {query}

        [검색 결과(근거)]
        {docs_text}
    """

    t_gen = time.perf_counter()
    gen_response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": gen_prompt}],
    )
    generated_answer = gen_response.choices[0].message.content
    print("\n[생성된 답변]")
    print(generated_answer)
    print(f"\n답변 생성 완료. 걸린 시간: {time.perf_counter() - t_gen:.4f}초")

    # 질문-답변 코사인 유사도 (OpenAI 임베딩)
    embed_query = client.embeddings.create(
        model="text-embedding-3-small", input=query
    ).data[0].embedding
    embed_answer = client.embeddings.create(
        model="text-embedding-3-small", input=generated_answer
    ).data[0].embedding

    vq_eval = np.array(embed_query)
    va_eval = np.array(embed_answer)
    cosine_sim_qa = float(np.dot(vq_eval, va_eval) / (np.linalg.norm(vq_eval) * np.linalg.norm(va_eval)))
    print("\n[질문-답변 코사인 유사도(OpenAI 임베딩)]")
    print(f"Cosine Similarity (Q vs Answer): {cosine_sim_qa:.4f}")



if __name__ == "__main__":
    main()
