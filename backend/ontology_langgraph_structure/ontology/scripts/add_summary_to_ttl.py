"""
TTL 파일에 hasSummary 속성 일괄 추가

CSV에서 category, title, summary를 읽고, TTL에서 # title 주석을 찾아
해당 블록의 메인 엔티티에 hasSummary 추가

처리 과정:
1. CSV에서 category, title, summary, 행 번호 읽기
2. TTL 파일에서 # title 주석 찾기
3. 주석 다음 블록에서 category와 label이 일치하는 메인 엔티티 찾기
4. 해당 엔티티의 rdfs:label 아래에 hasSummary 추가
5. 매칭되지 않는 CSV 행 번호를 .restack에 기록
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
    CSV에서 category, title, summary, 행 번호 로드
    
    Returns:
        [(row_num, category, title, summary), ...] 리스트 (행 번호는 1-based)
    """
    csv_data = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=1):  # 1-based
            category = row['category'].strip()
            title = row['title'].strip()
            summary = row['summary'].strip()
            
            if title and summary:
                csv_data.append((row_num, category, title, summary))
    
    print(f"📖 CSV에서 {len(csv_data)}개 항목 로드됨")
    return csv_data


def escape_ttl_string(s: str) -> str:
    """TTL 문자열 이스케이프"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')


def normalize_category(category: str) -> str:
    """category 정규화 (비교를 위해)"""
    # 괄호 제거, 공백 정리
    category = re.sub(r'\s*\([^)]*\)\s*', '', category)  # 괄호 내용 제거
    category = category.strip()
    return category


def type_to_category(entity_type: str) -> str:
    """rdf:type을 CSV category로 변환"""
    type_mapping = {
        'Person': '인물',
        'Event': '사건',
        'Battle': '사건',  # Battle은 Event의 하위
        'Policy': '정책',
        'Institution': '제도',
        'Document': '문헌',
        'Nation': '국가',
        'Place': '장소',
        'Object': '물품',
        'Role': '역할',
        'SocialClass': '사회계층'
    }
    # hist:Person -> Person
    type_name = entity_type.replace('hist:', '')
    return type_mapping.get(type_name, '')




def process_ttl_file(ttl_path: str, csv_data: list, output_path: str = None, restack_path: str = None):
    """
    TTL 파일을 처리하여 hasSummary 추가
    
    Args:
        ttl_path: 입력 TTL 파일 경로
        csv_data: [(row_num, category, title, summary), ...] 리스트
        output_path: 출력 TTL 파일 경로 (None이면 원본 덮어쓰기)
        restack_path: .restack 파일 경로
    """
    if output_path is None:
        output_path = ttl_path
    
    print(f"📄 TTL 파일 처리 중: {ttl_path}")
    
    # TTL 파일 읽기
    with open(ttl_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"   총 {len(lines)}줄 읽음")
    
    # 1단계: TTL 구조 분석 - 주석 블록과 엔티티 매핑
    print("   1단계: TTL 구조 분석 중...")
    
    # 주석 패턴: # title 또는 # title (category)
    comment_pattern = re.compile(r'^#\s*(.+)$')
    # rdf:type 패턴
    type_pattern = re.compile(r'^(hist:\S+)\s+rdf:type\s+(hist:\S+)')
    # rdfs:label 패턴
    label_pattern = re.compile(r'^(hist:\S+)\s+rdfs:label\s+"([^"]+)"')
    # hasSummary 패턴
    summary_pattern = re.compile(r'^(hist:\S+)\s+hist:hasSummary\s+')
    
    # 블록 구조: {comment_line_index: {'title': title, 'category': category, 'entities': [...]}}
    blocks = {}
    # 엔티티 정보: {uri: {'line': line_index, 'label': label, 'type': type, 'category': category, 'has_summary': bool}}
    entities = {}
    
    current_block_start = None
    current_block_info = None
    
    for i, line in enumerate(lines):
        # 주석 라인 찾기
        comment_match = comment_pattern.match(line)
        if comment_match:
            # 이전 블록 저장 (딕셔너리 복사)
            if current_block_start is not None and current_block_info:
                blocks[current_block_start] = {
                    'title': current_block_info['title'],
                    'category': current_block_info['category'],
                    'entities': list(current_block_info['entities'])  # 리스트 복사
                }
            
            # 새 블록 시작
            comment_text = comment_match.group(1).strip()
            # title과 category 분리
            title_match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', comment_text)
            if title_match:
                title = title_match.group(1).strip()
                category = normalize_category(title_match.group(2))
            else:
                title = comment_text
                category = ""
            
            current_block_start = i
            current_block_info = {
                'title': title,
                'category': category,
                'entities': []
            }
            continue
        
        # 엔티티 정보 수집 (주석 블록 내에서만)
        if current_block_start is not None:
            # rdf:type 찾기
            type_match = type_pattern.match(line)
            if type_match:
                uri = type_match.group(1)
                entity_type = type_match.group(2)
                
                # 엔티티가 이미 있으면 타입만 업데이트, 없으면 생성
                if uri not in entities:
                    entities[uri] = {
                        'line': i,
                        'label': '',
                        'type': entity_type,
                        'category': current_block_info['category'],  # 주석의 category 우선!
                        'has_summary': False
                    }
                else:
                    entities[uri]['type'] = entity_type
                    # category는 주석 것을 유지 (rdf:type으로 덮어쓰지 않음)
            
            # rdfs:label 찾기
            label_match = label_pattern.match(line)
            if label_match:
                uri = label_match.group(1)
                label = label_match.group(2)
                
                if uri not in entities:
                    entity_info = {
                        'line': i,
                        'label': label,
                        'type': '',
                        'category': current_block_info['category'],  # 주석의 category
                        'has_summary': False
                    }
                    entities[uri] = entity_info
                else:
                    entities[uri]['line'] = i  # label 라인으로 업데이트
                    entities[uri]['label'] = label
                
                if uri not in current_block_info['entities']:
                    current_block_info['entities'].append(uri)
            
            # hasSummary 찾기
            summary_match = summary_pattern.match(line)
            if summary_match:
                uri = summary_match.group(1)
                if uri in entities:
                    entities[uri]['has_summary'] = True
    
    # 마지막 블록 저장 (딕셔너리 복사)
    if current_block_start is not None and current_block_info:
        blocks[current_block_start] = {
            'title': current_block_info['title'],
            'category': current_block_info['category'],
            'entities': list(current_block_info['entities'])  # 리스트 복사
        }
    
    print(f"   - 발견된 주석 블록: {len(blocks)}개")
    print(f"   - 발견된 엔티티: {len(entities)}개")
    
    # 2단계: CSV 데이터와 TTL 블록 매칭
    print("   2단계: CSV와 TTL 매칭 중...")
    
    # CSV 데이터를 title로 인덱싱 (동명이인 처리 위해 category도 고려)
    csv_by_title = defaultdict(list)  # {title: [(row_num, category, summary), ...]}
    for row_num, category, title, summary in csv_data:
        csv_by_title[title].append((row_num, category, summary))
    
    # 매칭 결과
    lines_to_insert = {}  # {line_index: summary_line}
    matched_csv_rows = set()  # 매칭된 CSV 행 번호
    unmatched_csv_rows = []  # 매칭 안된 CSV 행 번호
    
    for block_start, block_info in blocks.items():
        title = block_info['title']
        block_category = block_info['category']
        
        
        if title not in csv_by_title:
            continue
        
        # 같은 title을 가진 CSV 항목들 중에서 category가 일치하는 것 찾기
        matched_csv_item = None
        for row_num, csv_category, summary in csv_by_title[title]:
            csv_cat_norm = normalize_category(csv_category)
            
            # category 매칭 (둘 다 있으면 정확히 일치, 하나만 있으면 통과)
            if block_category and csv_cat_norm:
                if block_category == csv_cat_norm:
                    matched_csv_item = (row_num, csv_category, summary)
                    break
            elif not block_category and not csv_cat_norm:
                # 둘 다 없으면 첫 번째 매칭
                matched_csv_item = (row_num, csv_category, summary)
                break
            elif not block_category:
                # TTL에 category 없으면 CSV category로 매칭
                matched_csv_item = (row_num, csv_category, summary)
                break
        
        if not matched_csv_item:
            # 매칭 안됨 - CSV 항목들 중 첫 번째를 unmatched로 기록
            for row_num, _, _ in csv_by_title[title]:
                if row_num not in matched_csv_rows:
                    unmatched_csv_rows.append(row_num)
            continue
        
        row_num, matched_csv_category, summary = matched_csv_item
        matched_csv_rows.add(row_num)
        matched_csv_cat_norm = normalize_category(matched_csv_category)
        
        # 블록 내에서 메인 엔티티 찾기 (label이 title과 일치하고 category도 일치)
        main_entity_uri = None
        for uri in block_info['entities']:
            if uri not in entities:
                if debug_mode:
                    print(f"    [WARN] 엔티티 {uri}가 entities 딕셔너리에 없음")
                continue
            
            if entities[uri]['label'] == title:
                # category도 확인
                entity_category = entities[uri]['category']
                
                if debug_mode:
                    print(f"    엔티티 매칭: {uri}")
                    print(f"      label='{entities[uri]['label']}' == title='{title}': {entities[uri]['label'] == title}")
                    print(f"      entity_category='{entity_category}', matched_csv_cat_norm='{matched_csv_cat_norm}'")
                
                # category 매칭 확인
                if not entity_category or not matched_csv_cat_norm or entity_category == matched_csv_cat_norm:
                    main_entity_uri = uri
                    if debug_mode:
                        print(f"      -> category 매칭 성공!")
                    break
                elif debug_mode:
                    print(f"      -> category 매칭 실패")
        
        if not main_entity_uri:
            # 메인 엔티티 못 찾음
            if debug_mode:
                print(f"  -> 메인 엔티티 못 찾음")
            unmatched_csv_rows.append(row_num)
            continue
        
        # hasSummary 이미 있으면 스킵 (이미 추가된 경우)
        if entities[main_entity_uri]['has_summary']:
            if debug_mode:
                print(f"  -> 이미 hasSummary 있음, 스킵")
            continue
        
        # rdfs:label 라인 찾기 (label 라인에 추가해야 함)
        label_line = None
        for i in range(entities[main_entity_uri]['line'], min(entities[main_entity_uri]['line'] + 10, len(lines))):
            label_match = label_pattern.match(lines[i])
            if label_match and label_match.group(1) == main_entity_uri:
                label_line = i
                break
        
        if label_line is None:
            if debug_mode:
                print(f"  -> rdfs:label 라인을 찾지 못함")
            unmatched_csv_rows.append(row_num)
            continue
        
        if debug_mode:
            print(f"  -> hasSummary 추가 예정: {main_entity_uri} (라인 {label_line+1} 다음)")
        
        # rdfs:label 라인 다음에 hasSummary 추가
        escaped_summary = escape_ttl_string(summary)
        summary_line = f'{main_entity_uri} hist:hasSummary "{escaped_summary}" .\n'
        
        lines_to_insert[label_line + 1] = summary_line
    
    print(f"   - 매칭된 CSV 항목: {len(matched_csv_rows)}개")
    print(f"   - 추가할 hasSummary: {len(lines_to_insert)}개")
    print(f"   - 매칭 안된 CSV 항목: {len(unmatched_csv_rows)}개")
    
    # 3단계: 새 TTL 파일 생성
    if lines_to_insert:
        print("   3단계: 새 TTL 파일 생성 중...")
        
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
    
    # 4단계: .restack 파일 생성
    if restack_path and unmatched_csv_rows:
        print("   4단계: .restack 파일 생성 중...")
        
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
