"""
TTL 파일에 hasSummary 속성 일괄 추가

CSV에서 title, summary를 읽고, TTL에서 # title 주석을 찾아
해당 블록의 메인 엔티티에 hasSummary 추가

처리 과정:
1. TTL 파일을 한 번 읽어서 모든 주석 블록 인덱싱
2. CSV에서 순차적으로 title, summary 읽기
3. 이미 TTL에 summary가 있는 항목 제외
4. CSV의 title과 TTL 블록의 title이 일치하면:
   - 해당 블록의 rdfs:label 다음에 hasSummary 추가
   - CSV 다음 항목으로 이동
5. 매칭되지 않는 CSV 항목은 .restack에 기록
"""

import os
import csv
import sys
import re
from pathlib import Path
from collections import defaultdict

# CSV 필드 크기 제한 증가
csv.field_size_limit(sys.maxsize)


def load_csv_data(csv_path: str) -> list:
    """
    CSV에서 title, summary 순차적으로 로드
    
    Returns:
        [(row_num, title, summary), ...] 리스트 (행 번호는 1-based)
    """
    csv_data = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=1):  # 1-based
            title = row['title'].strip()
            summary = row['summary'].strip()
            
            if title and summary:
                csv_data.append((row_num, title, summary))
    
    print(f"📖 CSV에서 {len(csv_data)}개 항목 로드됨")
    return csv_data


def escape_ttl_string(s: str) -> str:
    """TTL 문자열 이스케이프"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')


def extract_title_from_comment(comment_text: str) -> str:
    """
    주석에서 title 추출
    예: "이순신 (인물)" -> "이순신"
    예: "가" -> "가"
    """
    # 괄호가 있으면 괄호 앞의 텍스트만 추출
    match = re.match(r'^(.+?)\s*\([^)]+\)\s*$', comment_text)
    if match:
        return match.group(1).strip()
    return comment_text.strip()


def index_ttl_blocks(lines: list) -> dict:
    """
    TTL 파일의 모든 주석 블록을 인덱싱
    
    Returns:
        {title: {'comment_line': int, 'label_line': int, 'has_summary': bool, 'uri': str}, ...}
    """
    blocks = {}
    
    # 주석 패턴: # title 또는 # title (category)
    comment_pattern = re.compile(r'^#\s*(.+)$')
    # rdfs:label 패턴
    label_pattern = re.compile(r'^(hist:\S+)\s+rdfs:label\s+"([^"]+)"')
    # hasSummary 패턴
    summary_pattern = re.compile(r'^(hist:\S+)\s+hist:hasSummary\s+')
    
    current_block = None
    current_block_title = None
    found_label = False
    
    for i, line in enumerate(lines):
        # 새 블록 시작 (주석)
        comment_match = comment_pattern.match(line)
        if comment_match:
            # 이전 블록 저장
            if current_block and current_block_title and found_label:
                blocks[current_block_title] = current_block
            
            # 새 블록 시작
            comment_text = comment_match.group(1).strip()
            current_block_title = extract_title_from_comment(comment_text)
            current_block = {
                'comment_line': i,
                'label_line': None,
                'has_summary': False,
                'uri': None
            }
            found_label = False
            continue
        
        # 현재 블록에서 label 찾기
        if current_block and not found_label:
            label_match = label_pattern.match(line)
            if label_match:
                uri = label_match.group(1)
                label = label_match.group(2)
                
                # label이 현재 블록의 title과 일치하면 저장
                if label == current_block_title:
                    current_block['label_line'] = i
                    current_block['uri'] = uri
                    found_label = True
        
        # hasSummary 찾기
        if current_block and found_label:
            summary_match = summary_pattern.match(line)
            if summary_match and summary_match.group(1) == current_block['uri']:
                current_block['has_summary'] = True
    
    # 마지막 블록 저장
    if current_block and current_block_title and found_label:
        blocks[current_block_title] = current_block
    
    print(f"📊 TTL에서 발견된 블록: {len(blocks)}개")
    return blocks


def process_ttl_file(ttl_path: str, csv_data: list, output_path: str = None, restack_path: str = None):
    """
    TTL 파일을 처리하여 hasSummary 추가
    """
    if output_path is None:
        output_path = ttl_path
    
    print(f"📄 TTL 파일 처리 중: {ttl_path}")
    
    # TTL 파일 읽기
    with open(ttl_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"   총 {len(lines)}줄 읽음")
    
    # 1단계: TTL 블록 인덱싱
    print("   1단계: TTL 블록 인덱싱 중...")
    ttl_blocks = index_ttl_blocks(lines)
    
    # 이미 summary가 있는 블록 수집
    existing_summaries = {title for title, block in ttl_blocks.items() if block['has_summary']}
    print(f"   - 이미 summary가 있는 블록: {len(existing_summaries)}개")
    
    # 2단계: CSV 필터링 (이미 summary가 있는 항목 제외)
    print("   2단계: CSV 필터링 중...")
    filtered_csv_data = []
    skipped_count = 0
    for row_num, title, summary in csv_data:
        if title in existing_summaries:
            skipped_count += 1
        else:
            filtered_csv_data.append((row_num, title, summary))
    
    print(f"   - 이미 summary 있어서 건너뛴 항목: {skipped_count}개")
    print(f"   - 추가할 항목: {len(filtered_csv_data)}개")
    
    if not filtered_csv_data:
        print("   ⚠️ 추가할 summary가 없습니다.")
        return
    
    # 3단계: CSV를 순차적으로 처리하면서 TTL 블록 찾기
    print("   3단계: CSV와 TTL 매칭 중...")
    
    lines_to_insert = {}  # {line_index: summary_line}
    matched_csv_rows = set()
    
    for row_num, csv_title, csv_summary in filtered_csv_data:
        # TTL 블록에서 해당 title 찾기
        if csv_title in ttl_blocks:
            block = ttl_blocks[csv_title]
            
            # 이미 summary가 있으면 건너뛰기
            if block['has_summary']:
                continue
            
            # label 라인이 없으면 건너뛰기
            if block['label_line'] is None:
                continue
            
            # summary 추가
            uri = block['uri']
            escaped_summary = escape_ttl_string(csv_summary)
            summary_line = f'{uri} hist:hasSummary "{escaped_summary}" .\n'
            lines_to_insert[block['label_line'] + 1] = summary_line
            matched_csv_rows.add(row_num)
    
    # 매칭되지 않은 항목 수집
    unmatched_csv_rows = []
    for row_num, title, summary in filtered_csv_data:
        if row_num not in matched_csv_rows:
            unmatched_csv_rows.append(row_num)
    
    print(f"   - 매칭된 항목: {len(matched_csv_rows)}개")
    print(f"   - 추가할 hasSummary: {len(lines_to_insert)}개")
    print(f"   - 매칭 안된 항목: {len(unmatched_csv_rows)}개")
    
    # 4단계: 새 TTL 파일 생성
    if lines_to_insert:
        print("   4단계: 새 TTL 파일 생성 중...")
        
        # 삽입 위치를 역순으로 정렬
        sorted_inserts = sorted(lines_to_insert.items(), key=lambda x: x[0], reverse=True)
        
        for insert_index, summary_line in sorted_inserts:
            lines.insert(insert_index, summary_line)
        
        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ 완료: {output_path}")
        print(f"   - 추가된 hasSummary: {len(lines_to_insert)}개")
        print(f"   - 총 라인 수: {len(lines)}개")
    else:
        print("   ⚠️ 추가할 summary가 없습니다.")
    
    # 5단계: .restack 파일 생성
    if restack_path and unmatched_csv_rows:
        print("   5단계: .restack 파일 생성 중...")
        
        # 중복 제거 및 정렬
        unique_unmatched = sorted(set(unmatched_csv_rows))
        
        with open(restack_path, 'w', encoding='utf-8') as f:
            for row_num in unique_unmatched:
                f.write(f"{row_num}\n")
        
        print(f"✅ .restack 파일 생성: {restack_path}")
        print(f"   - 기록된 행 번호: {len(unique_unmatched)}개")


def main():
    """메인 함수"""
    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    ttl_input_path = script_dir.parent / "instances/korean_history_instances.ttl"
    ttl_output_path = script_dir.parent / "instances/korean_history_instances_with_summary.ttl"
    restack_path = script_dir.parent / "instances/.restack"
    
    # 명령줄 인자 처리
    # --inplace: 원본 파일 덮어쓰기
    inplace = "--inplace" in sys.argv
    
    if inplace:
        output_path = str(ttl_input_path)
        print("⚠️ 원본 파일 덮어쓰기 모드")
    else:
        output_path = str(ttl_output_path)
        print(f"📦 새 파일로 저장: {ttl_output_path.name}")
    
    # CSV 로드
    csv_data = load_csv_data(str(csv_path))
    
    # TTL 처리
    process_ttl_file(str(ttl_input_path), csv_data, output_path, str(restack_path))
    
    print("\n🎉 작업 완료!")


if __name__ == "__main__":
    main()
