import time
import json

from db.db_connetion import create_connection
from db.vector_store import create_vectorstore
from backend.db_pipeline.common.embedding_model import get_embedding

INDEX_NAME = "rag_embeddings"  # 인덱스 이름 한 곳에서 관리
MIN_SCORE = 0.3  # 코사인 유사도 점수 컷 (필요 시 조정)


def run_retriever(vectorstore, query: str):
    """미리 인덱싱된 ES에서 검색만 수행"""
    t0 = time.perf_counter()  # 검색 시작 시각
    results = vectorstore.similarity_search_with_score(query, k=3, min_score=MIN_SCORE)
    t1 = time.perf_counter()  # 검색 종료 시각

    context = ""
    top_score = None
    for doc, score in results:
        if context == "":
            context = doc.page_content[:120]
            top_score = score
        print("=" * 50)
        print(f"점수: {score:.4f}")
        print(f"내용: {doc.page_content[:120]}..")
    print(f"검색 시간: {t1 - t0:.3f}초")
    return context, top_score, t1 - t0


if __name__ == "__main__":
    # 사전 요구사항: ingest_data.py를 실행해 인덱스를 만들어 둡니다.
    es_client = create_connection()
    embeddings = get_embedding()

    # 인덱스를 대상으로 검색 전용 VectorStore 생성
    vectorstore = create_vectorstore(es_client, INDEX_NAME, embeddings)
    print("Elasticsearch vectorstore 준비 완료.")

    questions = [
    "조선 건국",
    "조선 시대에 왕들은 무엇을 했습니까?",
    "조선 시대에 아이들은 학교에서 무엇을 공부했나요?",
    "왜 위화도 회군이 일어났나요?",
    "정여립의 반란은 무엇이었습니까?",
    "기묘사화는 왜 일어났는가?",
    "신해통공 개혁은 왜 시행되었는가?",
    "세종대왕에 대해 말해줘.",
    "흥선대원군은 어떤 사람이었나?",
    "이순신 장군은 누구였나요?",
    "동학 농민 혁명을 누가 이끌었는가?",
    "정도전이 매우 유명했다고 들었는데 그가 어떤 제도들을 만들었고, 그것들은 무엇에 관한 것이었나?",
    "병자호란은 왜 일어났는가?",
    "임진왜란 중에 싸운 장군들에 대해 말해 주세요.",
    "명성황후의 암살은 어떻게 일어났나요?",
    "무엇이 동학 농민 혁명을 일으켰는가?",
    "임진왜란과 병자호란의 차이점은 무엇인가?",
    "조선 시대에서 가장 용감한 사람은 누구였나요?",
    "이순신과 권율의 관계는 무엇이었나?",
    "과거에 사람들은 어떻게 여행했나요? 자동차가 있었나요?",
    "오늘날과 비교하여, 옛날 사람들은 시장에서 무엇을 팔았나요?",
    "조선 시대의 궁궐은 어떻게 생겼나요?",
    "조선 시대에 아이들은 무엇을 하며 놀았나요?",
    "사람들은 과거에 집에서 어떻게 살았나요?",
    "옛날에 사람들은 생일을 축하하기 위해 무엇을 했나요?",
    "과거에 사람들은 시계 없이 시간을 어떻게 측정했나요?",
    "조선 시대의 가장 흥미로운 이야기를 들려 주세요.",
    "임진왜란의 연표를 설명하라.",
    "장영실이 어떻게 거중기를 발명했는지 그 이야기를 들려줘.",
    "갑신정변은 왜 일어났고, 그 결과 어떤 조약들이 체결되었는가?",
    "제물포 조약은 언제 일어났습니까?",
    "종묘가 유네스코 세계유산이라는 것이 사실인가요?",
    "명량해전은 이순신 제독이 지휘한 것이 사실입니까?",
    "한글은 정말 세종대왕이 창제했나요?",
    "조선 시대에 계급 제도가 존재했습니까?",
    "경복궁을 방문하면 무엇을 볼 수 있나요?",
    "조선 시대의 어떤 역사적 유적들이 오늘날에도 남아 있으며, 어디를 방문해야 하나요?",
    "명량해전은 어디에서 일어났나요? 그곳을 방문하고 싶습니다.",
    "exit"
    ]

    for query in questions:
        if query.lower() == "exit":
            break
        if not query:
            continue
        context, score, elapsed_time = run_retriever(vectorstore, query)

        # 질문 별 검색 속도 json으로 저장
        # 기존 파일 있으면 불러와서 append
        
        try:
            with open("search_times.json", "r", encoding="utf-8") as f:
                search_times = json.load(f)
        except FileNotFoundError:
            search_times = []

        search_times.append(
            {"query": query, "contents": context, "score": score, "time": elapsed_time}
        )

        with open("search_times.json", "w", encoding="utf-8") as f:
            json.dump(search_times, f, ensure_ascii=False, indent=4)
