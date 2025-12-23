from pathlib import Path
import json
from typing import List, Dict
from datasets import Dataset


def _read_jsonl(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_dataset(
    questions_path: str | Path,
    results_path: str | Path,
    use_lang: str = "ko",
) -> Dataset:
    """
    LangGraph 실행 결과 JSONL과 질문 JSONL을 합쳐 Ragas용 Dataset을 만든다.

    questions.jsonl 예시:
        {"persona_id": "...", "qtype": "...", "question_en": "...", "question_ko": "..."}

    results jsonl 예시 (LangGraph state 로그):
        {
          "query": "...",
          "final_answer": "...",
          "vector_evidences": [{"payload": {"content": "..."}, ...}, ...],
          "neo4j_results": [{"summary": "...", ...}]
        }

    Args:
        questions_path: 질문 jsonl 경로
        results_path: LangGraph 실행 결과 jsonl 경로 (필수)
        use_lang: "ko" 또는 "en" 중 질문 필드 선택

    Returns:
        HuggingFace Dataset (question, answer, contexts[, ground_truth], persona_id, qtype)
    """
    q_path = Path(questions_path)
    r_path = Path(results_path)

    questions = _read_jsonl(q_path)
    results = _read_jsonl(r_path)

    # 결과 맵핑: query 문자열을 키로 사용
    results_map: Dict[str, Dict] = {}
    for row in results:
        key = row.get("query") or row.get("question")
        if key:
            results_map[key] = row

    records = []
    for row in questions:
        question_text = row.get(f"question_{use_lang}") or row.get("question")
        if not question_text:
            continue

        merged = {
            "question": question_text,
            "persona_id": row.get("persona_id"),
            "qtype": row.get("qtype"),
        }

        res = results_map.get(question_text, {})
        merged["answer"] = res.get("final_answer") or res.get("answer", "")

        contexts: List[str] = res.get("contexts", [])

        # LangGraph state 형태라면 vector_evidences/neo4j_results에서 컨텍스트 추출
        for ev in res.get("vector_evidences", []):
            payload = ev.get("payload", {})
            content = payload.get("content")
            if content:
                contexts.append(content)
        for neo in res.get("neo4j_results", []):
            summary = neo.get("summary")
            if summary:
                contexts.append(summary)

        merged["contexts"] = contexts
        if "ground_truth" in res:
            merged["ground_truth"] = res["ground_truth"]

        records.append(merged)

    if not records:
        raise ValueError("질문/결과 데이터가 비어 있어 Dataset을 만들 수 없습니다.")

    return Dataset.from_list(records)


__all__ = ["load_dataset"]
