# test_search_speed.py

import time
from config import milvus_config
from db.connection import connect_milvus
from db.collection import get_collection
from embedding import get_embedding_model
import openai
import numpy as np

# -------------------------
# 검색 함수
# -------------------------
def search(collection, query: str, top_k: int = 5):
    # 1) 쿼리 embed
    embedding_model = get_embedding_model()
    query_vec = embedding_model.embed_query(query)

    # 2) Milvus 검색
    search_params = {
        "metric_type": "L2",      # 인덱스 타입과 동일해야 함
        "params": {"nprobe": 16}, # IVF_FLAT일 때 성능 조절 파라미터
    }

    results = collection.search(
        data=[query_vec],         # 리스트 형태로 넣어야 함
        anns_field="embedding",   # 검색 대상 필드
        param=search_params,
        limit=top_k,
        output_fields=["title", "summary", "category", "embedding"]
    )

    # 검색 결과와 함께 query_vec도 반환
    return results, query_vec


# -------------------------
# 메인 테스트 실행
# -------------------------
if __name__ == "__main__":
    # ===== 설정값 (테스트용) =====
    COS_THRESHOLD = 0.60  # 질문-문서 코사인 유사도 threshold (디버깅/필터링용)
    TOP_K = 5             # Milvus 상위 검색 개수

    print("Milvus 연결 중...")
    connect_milvus(milvus_config)

    print("컬렉션 가져오는 중...")
    collection = get_collection(
        milvus_config["collection_name"],
        milvus_config["alias"]
    )

    query = "조선에서 가장 용감한 사람은 누구야?"

    print(f"\n검색 쿼리: {query}")

    start = time.time()
    results, query_vec = search(collection, query, top_k=TOP_K)
    elapsed = time.time() - start
    print(f"\n검색 완료. 걸린 시간: {elapsed:.4f}초")
    print("-" * 50)

    # -----------------------------
    # 0) 질문-문서 코사인 유사도 계산 및 출력
    # -----------------------------
    vq_milvus = np.array(query_vec)
    doc_infos = []

    print("\n[Milvus 검색 결과별 코사인 유사도]")
    for idx, hit in enumerate(results[0]):
        doc_emb = hit.entity.get("embedding")
        vd = np.array(doc_emb)

        cosine_sim_doc = np.dot(vq_milvus, vd) / (
            np.linalg.norm(vq_milvus) * np.linalg.norm(vd)
        )

        info = {
            "idx": idx,
            "cosine_sim": float(cosine_sim_doc),
            "distance": float(hit.distance),
            "category": hit.entity.get("category"),
            "title": hit.entity.get("title"),
            "summary": hit.entity.get("summary"),
        }
        doc_infos.append(info)

        print(f"문서 {idx+1}:")
        print(f"  Milvus distance (L2): {info['distance']:.4f}")
        print(f"  Cosine Similarity (Q vs Doc): {info['cosine_sim']:.4f}")
        print(f"  category: {info['category']}")
        print(f"  title: {info['title']}")
        print(f"  summary: {info['summary']}")
        print("-" * 30)

    # threshold 이상인 문서만 "상대적으로 관련 있음"으로 간주 (RAG는 계속 사용)
    relevant_docs = [d for d in doc_infos if d["cosine_sim"] >= COS_THRESHOLD]

    if len(relevant_docs) == 0:
        print(f"\n[INFO] 코사인 유사도 {COS_THRESHOLD} 이상인 문서가 없습니다."
              " (그래도 아래 문서들만을 근거로 답변을 생성합니다.)")
        # 근거가 전혀 없더라도, doc_infos 자체를 근거로 사용
        docs_for_prompt = doc_infos
    else:
        print(f"\n[INFO] 코사인 유사도 {COS_THRESHOLD} 이상인 문서가 "
              f"{len(relevant_docs)}개 있습니다. 이 문서들을 우선 근거로 사용합니다.")
        docs_for_prompt = relevant_docs

    # -----------------------------
    # 1) GPT 기반 검색 결과 요약/답변 생성 (항상 RAG 기반)
    # -----------------------------
    client = openai.OpenAI()

    # 프롬프트에 넣을 문서 텍스트 구성
    docs_text = "\n\n".join(
        [
            f"[문서 {i+1}]\n"
            f"(cosine_sim={d['cosine_sim']:.4f})\n"
            f"category: {d['category']}\n"
            f"title: {d['title']}\n"
            f"summary: {d['summary']}"
            for i, d in enumerate(docs_for_prompt)
        ]
    )

    # 항상 "근거 기반"으로만 답변하도록 고정
    gen_prompt = f"""
        너는 역사 전문 RAG 기반 답변 생성기이다.
        아래에는 사용자의 질문과 벡터 검색으로 찾은 문서들(근거)이 포함된다.

        다음 원칙을 반드시 지켜라.
        1. 아래 [검색 결과(근거)]에 포함된 정보만 사용하여 답변을 구성하라.
        2. 근거 문서에 명시되지 않은 내용을 너의 일반 지식으로 보충하거나 추론하여
        사실처럼 단정적으로 말하지 마라.
        3. 만약 근거 문서들이 질문에 직접적으로 답할 수 있는 정보를 거의 제공하지 않는다면,
        그 사실을 솔직하게 밝히고,
        "현재 제공된 근거만으로는 질문에 정확히 답하기 어렵다"는 취지로 설명하라.
        4. 그 경우에도, 근거 문서들이 다루는 인물·시대·사료의 성격을 간단히 정리하고,
        왜 이 근거들로는 질문에 답하기 어려운지를 논리적으로 설명하라.

        출력 형식 (중요! 형식을 절대 바꾸지 마라):
        Q. {{사용자 질문}}
        A. [본문]
        - 5~10문장 분량, 2~3개의 자연스러운 단락으로 구성
        - 반드시 검색 결과(근거)에 기반한 사실만 포함
        - 근거 문서 번호를 (참고: 1, 3)과 같이 표기
        - 단정적 단어는 최소화하고, 역사적 해석의 여지나 다양성도 언급

        [요약]
        - 본문의 핵심 요지만 2~3문장으로 정리

        [참고 근거]
        - 근거1 요약: 문서 1의 핵심 내용 요약
        - 근거2 요약: 문서 2의 핵심 내용 요약
        - 근거3 요약: 문서 3의 핵심 내용 요약
        (※ 실제 문서 수에 맞춰 번호는 자동 조정)

        ----------------------------------
        [질문]
        {query}

        [검색 결과(근거)]
        {docs_text}
    """

    start_generate = time.time()

    gen_response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "user", "content": gen_prompt}
        ]
    )

    generated_answer = gen_response.choices[0].message.content
    print("\n[생성된 답변]")
    print(generated_answer)
    elapsed1 = time.time() - start_generate
    print(f"\n답변 생성 완료. 걸린 시간: {elapsed1:.4f}초")

    # -----------------------------
    # 2) 질문-답변 코사인 유사도 계산 (OpenAI 임베딩)
    # -----------------------------
    embed_query = client.embeddings.create(
        model="text-embedding-3-small",  # 임베딩용 모델
        input=query
    ).data[0].embedding

    embed_answer = client.embeddings.create(
        model="text-embedding-3-small",
        input=generated_answer
    ).data[0].embedding

    vq_eval = np.array(embed_query)
    va_eval = np.array(embed_answer)

    cosine_sim_qa = np.dot(vq_eval, va_eval) / (
        np.linalg.norm(vq_eval) * np.linalg.norm(va_eval)
    )

    print("\n[질문-답변 코사인 유사도(OpenAI 임베딩)]")
    print(f"Cosine Similarity (Q vs Answer): {cosine_sim_qa:.4f}")

    # -----------------------------
    # 3) GPT 기반 검색 결과 평가 (문서별 관련성 점수)
    # -----------------------------
    eval_prompt = f"""
        너는 검색 시스템의 평가자이다.
        아래에는 사용자의 질문과 벡터 검색으로 찾은 문서들이 있다.
        각 문서가 질문에 얼마나 잘 답변할 수 있는지 0부터 1 사이 점수로 평가해라.

        - 0부터 1 사이 점수로 평가해라.
        - 각 문서마다 한 줄로 "문서번호: 점수, 간단한 이유" 형식으로 출력해라.
        - 추가 설명, 다른 말은 하지 말고 지정한 형식만 출력해라.

        [질문]
        {query}

        [문서들]
        {docs_text}
    """

    eval_response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "user", "content": eval_prompt}
        ]
    )

    judge_result = eval_response.choices[0].message.content

    print("\n[GPT 기반 검색 결과 평가]")
    print(judge_result)
