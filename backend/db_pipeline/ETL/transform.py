"""
Transform: CSV 데이터 정규화 + 청킹

1. Extract: encykorea_cleaned6.csv 읽기
2. Normalize: 데이터 정규화 (공백, 특수문자 제거)
3. Chunking: contents 긴 텍스트 청킹 (500자 단위, 100자 오버랩)
4. Output: transformed_chunks.json 생성
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict


# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_CSV = DATA_DIR / "encykorea_cleaned6.csv"
OUTPUT_JSON = DATA_DIR / "transformed_chunks.json"

# 청킹 파라미터
CHUNK_SIZE = 500  # 500자 단위
OVERLAP_SIZE = 100  # 100자 오버랩


def normalize_text(text: str) -> str:
    """
    텍스트 정규화

    - 연속된 공백 → 단일 공백
    - 특수 유니코드 제거
    - 앞뒤 공백 제거
    """
    if not text or not isinstance(text, str):
        return ""

    # 연속 공백 → 단일 공백
    text = re.sub(r'\s+', ' ', text)

    # Zero-width characters 제거
    text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)

    # BOM 제거
    text = text.replace('\ufeff', '')

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP_SIZE) -> List[Dict]:
    """
    긴 텍스트를 청킹

    Args:
        text: 청킹할 텍스트
        chunk_size: 청크 크기 (기본 500자)
        overlap: 오버랩 크기 (기본 100자)

    Returns:
        [{"chunk_id": 0, "text": "...", "start": 0, "end": 500}, ...]
    """

    if not text or len(text) <= chunk_size:
        # 청킹 불필요
        return [{"chunk_id": 0, "text": text, "start": 0, "end": len(text)}]

    chunks = []
    chunk_id = 0
    start = 0

    while start < len(text):
        end = start + chunk_size

        # 마지막 청크인 경우
        if end >= len(text):
            chunk_text = text[start:]
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "start": start,
                "end": len(text)
            })
            break

        # 문장 경계에서 자르기 (마침표, 느낌표, 물음표)
        # 청크 끝에서 역방향으로 100자 이내에서 문장 경계 찾기
        search_start = max(end - 100, start)
        search_text = text[search_start:end]

        # 문장 경계 찾기
        sentence_endings = ['.', '!', '?', '。']
        best_split = -1

        for i in range(len(search_text) - 1, -1, -1):
            if search_text[i] in sentence_endings:
                # 마침표 뒤에 공백이 있는지 확인
                if i + 1 < len(search_text) and search_text[i + 1] == ' ':
                    best_split = search_start + i + 2  # 마침표 + 공백 다음
                    break
                elif i + 1 == len(search_text):
                    best_split = search_start + i + 1
                    break

        # 문장 경계를 찾았으면 그곳에서 자르기
        if best_split > start:
            end = best_split

        chunk_text = text[start:end]
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "start": start,
            "end": end
        })

        # 다음 청크는 오버랩을 고려하여 시작
        start = end - overlap
        chunk_id += 1

    return chunks


def transform_csv_to_chunks() -> List[Dict]:
    """
    CSV 데이터를 읽어 정규화 + 청킹하여 JSON 구조로 변환

    Returns:
        [
            {
                "doc_id": "doc_0",
                "category": "물품",
                "title": "가",
                "summary": "죄수의 목에 채우는 형구.",
                "chunks": [
                    {"chunk_id": 0, "text": "...", "start": 0, "end": 500},
                    ...
                ]
            },
            ...
        ]
    """

    # CSV 필드 크기 제한 증가 (큰 contents 필드 처리)
    import sys
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)

    transformed_data = []

    print(f"📖 Reading CSV: {INPUT_CSV}")

    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        # BOM 제거
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]

        # CSV 파싱
        reader = csv.DictReader(content.splitlines())

        for idx, row in enumerate(reader):
            # 데이터 추출
            category = normalize_text(row.get('category', ''))
            title = normalize_text(row.get('title', ''))
            summary = normalize_text(row.get('summary', ''))
            contents = normalize_text(row.get('contents', ''))

            # 청킹 (contents만)
            content_chunks = chunk_text(contents, chunk_size=CHUNK_SIZE, overlap=OVERLAP_SIZE)

            # 문서 구조 생성
            doc = {
                "doc_id": f"doc_{idx}",
                "category": category,
                "title": title,
                "summary": summary,
                "contents_length": len(contents),
                "num_chunks": len(content_chunks),
                "chunks": content_chunks
            }

            transformed_data.append(doc)

            # 진행상황 출력
            if (idx + 1) % 1000 == 0:
                print(f"  ├─ Processed: {idx + 1} documents")

    print(f"  └─ Total documents: {len(transformed_data)}")

    return transformed_data


def main():
    """메인 실행 함수"""

    print("="*70)
    print("ETL Transform: CSV → Normalized + Chunked JSON")
    print("="*70)

    # Transform
    transformed_data = transform_csv_to_chunks()

    total_chunks = sum(doc["num_chunks"] for doc in transformed_data)
    print(f"\n✅ 총 {len(transformed_data):,}개 문서, {total_chunks:,}개 청크 생성")

    # JSON 저장
    print(f"\n💾 Saving to: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({"documents": transformed_data}, f, ensure_ascii=False, indent=2)

    print(f"✅ Transform completed!")
    print(f"  └─ Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
