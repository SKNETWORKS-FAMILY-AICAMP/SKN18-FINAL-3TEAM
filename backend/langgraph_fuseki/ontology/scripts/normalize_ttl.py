"""
TTL 파일 정규화 스크립트 (v3 - 성능 최적화)

문제:
- 한글 URI: hist:Event_갑술환국 → Jena Reasoner 파싱 실패
- 한글 프로퍼티: hist:has두활Original → 파싱 실패
- 특수문자: 괄호(), 하이픈-, 점. 등 → TTL 문법 오류

해결:
- 한글 URI를 영어/숫자 ID로 변환 (해시 기반)
- 한글 프로퍼티를 영어로 변환
- 한글은 rdfs:label에만 유지
- 특수문자 제거
- 정규식 사용하여 한 번에 치환 (성능 최적화)
"""

import re
import hashlib
from pathlib import Path


def generate_safe_id(text: str) -> str:
    """
    텍스트를 안전한 ASCII ID로 변환

    예: "갑술환국(갑술옥사)" → "abc123"
    """
    hash_id = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    return hash_id


def normalize_property(prop: str) -> str:
    """
    프로퍼티 이름 정규화

    예: "has두활Original" → "hasDuHwalOriginal"
    예: "hasWeightFor(정조시기)" → "hasWeightFor_jeongjo"
    """
    # 괄호 제거 및 내용을 접미사로 변환
    if '(' in prop or '（' in prop:
        prop = re.sub(r'[()（）]', '_', prop)
        prop = prop.rstrip('_')

    # 한글이 있으면 해시로 변환
    if re.search(r'[가-힣]', prop):
        # 한글 부분만 해시로 변환
        korean_parts = re.findall(r'[가-힣]+', prop)
        for kp in korean_parts:
            prop = prop.replace(kp, generate_safe_id(kp))

    return prop


def normalize_uri(uri_part: str) -> tuple[str, str]:
    """
    URI 부분을 정규화

    입력: "Event_갑술환국(갑술옥사)"
    출력: ("Event_abc123", "갑술환국(갑술옥사)")
    """
    # 전체 URI에서 한글/특수문자 확인 (점(.)도 특수문자로 간주)
    has_korean = bool(re.search(r'[가-힣]', uri_part))
    has_special = bool(re.search(r'[()（）\-\s,;:\'"\[\]{}\.]', uri_part))

    if not (has_korean or has_special):
        return uri_part, ""

    # 타입과 이름 분리
    if '_' in uri_part:
        parts = uri_part.split('_', 1)
        entity_type = parts[0]
        entity_name = parts[1] if len(parts) > 1 else uri_part
    else:
        entity_type = uri_part
        entity_name = uri_part

    # 전체를 해시로 변환
    safe_id = generate_safe_id(uri_part)
    new_uri_part = f"{entity_type}_{safe_id}"
    return new_uri_part, entity_name


def normalize_ttl_file(input_path: str, output_path: str):
    """
    TTL 파일을 정규화하여 Jena Reasoner가 파싱할 수 있도록 변환
    """

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_path}")

    print(f"[1/5] URI 정규화")
    print(f"  입력 파일: {input_path}")

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # ========== 1. URI 정규화 ==========
    uri_mapping = {}
    label_mapping = {}

    # 모든 hist: URI 찾기
    # TTL 문법상 URI는 공백, 세미콜론, 점+공백으로 끝남
    # URI 끝의 점은 문장 끝이므로 제거해야 함
    # 매칭: hist: 뒤의 모든 문자, 단 공백/세미콜론 전까지
    uri_pattern = re.compile(r'hist:([^\s;]+)')
    all_uris = set(uri_pattern.findall(content))

    # URI 끝의 점 제거 (예: Person_abc. → Person_abc)
    cleaned_uris = set()
    for uri in all_uris:
        cleaned_uri = uri.rstrip('.')
        if cleaned_uri:
            cleaned_uris.add(cleaned_uri)
    all_uris = cleaned_uris

    print(f"  발견된 URI: {len(all_uris)}개")

    for uri_part in all_uris:
        new_uri_part, original_name = normalize_uri(uri_part)
        if new_uri_part != uri_part:
            uri_mapping[uri_part] = new_uri_part
            if original_name:
                label_mapping[new_uri_part] = original_name

    print(f"  변환 필요한 URI: {len(uri_mapping)}개")

    # URI 치환 (정규식 사용하여 한 번에 처리 - 성능 최적화)
    print(f"  URI 치환 중...")

    def replace_uri(match):
        """URI 치환 함수 (re.sub 콜백)"""
        prefix = match.group(1)  # 'hist:'
        uri_part = match.group(2)  # URI 부분
        # URI 끝의 점 제거
        uri_cleaned = uri_part.rstrip('.')
        # 매핑에서 찾기
        new_uri = uri_mapping.get(uri_cleaned, uri_cleaned)
        return f'{prefix}{new_uri}'

    # hist:XXX 패턴을 찾아서 치환 (공백/세미콜론 전까지)
    uri_replace_pattern = re.compile(r'(hist:)([^\s;]+)')
    normalized_content = uri_replace_pattern.sub(replace_uri, content)

    # ========== 2. 프로퍼티 정규화 ==========
    print(f"[2/5] 프로퍼티 정규화")
    prop_pattern = re.compile(r'hist:([a-zA-Z]+[가-힣()（）]+[^\s]*)')
    all_props = set(prop_pattern.findall(normalized_content))
    print(f"  발견된 비표준 프로퍼티: {len(all_props)}개")

    prop_mapping = {}
    for prop in all_props:
        new_prop = normalize_property(prop)
        if new_prop != prop:
            prop_mapping[prop] = new_prop

    print(f"  변환 필요한 프로퍼티: {len(prop_mapping)}개")

    # 프로퍼티 치환 (단어 경계 확인하여 부분 매칭 방지)
    for old_prop, new_prop in prop_mapping.items():
        # hist:프로퍼티 패턴만 정확히 매칭 (뒤에 공백이나 세미콜론)
        pattern = re.compile(r'hist:' + re.escape(old_prop) + r'(?=\s|;)')
        normalized_content = pattern.sub(f'hist:{new_prop}', normalized_content)

    # ========== 3. 잘못된 문법 수정 ==========
    print(f"[3/5] 문법 수정")
    # 잘못된 괄호 제거
    normalized_content = re.sub(r'hist:(\w+)\(([^)]+)\)', r'hist:\1_\2', normalized_content)
    # 남은 한글 괄호 처리
    normalized_content = re.sub(r'hist:(\w+)（([^）]+)）', r'hist:\1_\2', normalized_content)

    # Python 스타일 불리언 값을 TTL 형식으로 변환
    # True → true, False → false (소문자로 변환)
    bool_count = len(re.findall(r'\bTrue\b|\bFalse\b', normalized_content))
    normalized_content = re.sub(r'\bTrue\b', 'true', normalized_content)
    normalized_content = re.sub(r'\bFalse\b', 'false', normalized_content)
    if bool_count > 0:
        print(f"  불리언 값 변환: {bool_count}개 (True/False → true/false)")

    # ========== 4. 누락된 rdfs:label 추가 ==========
    lines = normalized_content.split('\n')
    new_lines = []
    existing_labels = set()

    label_pattern = re.compile(r'(hist:[^\s]+)\s+rdfs:label\s+"([^"]+)"')
    for line in lines:
        match = label_pattern.search(line)
        if match:
            existing_labels.add(match.group(1))

    labels_to_add = {}
    for new_uri, original_name in label_mapping.items():
        full_uri = f'hist:{new_uri}'
        if full_uri not in existing_labels:
            labels_to_add[full_uri] = original_name

    for line in lines:
        new_lines.append(line)

        type_match = re.match(r'(hist:[^\s]+)\s+rdf:type\s+(hist:[^\s]+)\s*\.', line)
        if type_match:
            uri = type_match.group(1)
            if uri in labels_to_add:
                label = labels_to_add[uri]
                new_lines.append(f'{uri} rdfs:label "{label}" .')
                del labels_to_add[uri]

    # ========== 5. 최종 정리 ==========
    final_content = '\n'.join(new_lines)

    print(f"[4/5] 최종 정리")

    # 남은 한글 문자가 있는 프로퍼티 제거 (주석 처리)
    remaining_korean_props = re.findall(r'hist:[a-zA-Z]*[가-힣]+[^\s]*', final_content)
    if remaining_korean_props:
        print(f"  경고: 남은 한글 프로퍼티 {len(set(remaining_korean_props))}개 발견, 주석 처리")
        for prop in set(remaining_korean_props):
            lines_with_prop = [l for l in final_content.split('\n') if prop in l]
            for line in lines_with_prop:
                final_content = final_content.replace(line, f'# REMOVED (korean prop): {line}')

    # JSON/dict 형태의 값이 있는 줄 제거 (유효하지 않은 TTL)
    lines = final_content.split('\n')
    cleaned_lines = []
    removed_json_count = 0
    for line in lines:
        # {로 시작하는 값이 있는 줄 감지 (문자열 안의 {는 제외)
        if re.search(r'\s+\{[\'"]', line) and 'rdfs:label' not in line:
            cleaned_lines.append(f'# REMOVED (json value): {line}')
            removed_json_count += 1
        else:
            cleaned_lines.append(line)

    if removed_json_count > 0:
        print(f"  경고: JSON 형태 값 {removed_json_count}개 줄 주석 처리")

    final_content = '\n'.join(cleaned_lines)

    # 잘못된 URI 형태 수정 (끝에 괄호가 붙은 경우)
    # hist:Event_abc123) → hist:Event_abc123
    final_content = re.sub(r'(hist:[A-Za-z]+_[a-f0-9]+)\)', r'\1', final_content)

    # 여전히 문제가 있는 URI 제거
    # 먼저 문제가 있는 URI를 수집
    lines = final_content.split('\n')
    invalid_uris = set()

    for line in lines:
        if line.startswith('#'):
            continue
        # URI에 비ASCII 문자가 남아있는지 확인
        korean_uri_match = re.search(r'(hist:[^\s]*[가-힣]+[^\s]*)', line)
        if korean_uri_match:
            invalid_uris.add(korean_uri_match.group(1))
        # URI에 잘못된 특수문자가 있는지 확인 (점 제외)
        special_uri_match = re.search(r'(hist:[A-Za-z]+_[^\s]*[(),;:]+[^\s]*)', line)
        if special_uri_match:
            invalid_uris.add(special_uri_match.group(1))

    if len(invalid_uris) > 0:
        print(f"  경고: 잘못된 URI {len(invalid_uris)}개 발견")

    # 문제 URI를 포함하는 모든 줄 제거
    final_lines = []
    removed_invalid = 0
    for line in lines:
        should_remove = False
        for invalid_uri in invalid_uris:
            if invalid_uri in line:
                should_remove = True
                break

        if should_remove:
            # 완전히 제거 (주석 처리 대신)
            removed_invalid += 1
        else:
            final_lines.append(line)

    if removed_invalid > 0:
        print(f"  경고: 잘못된 URI 관련 {removed_invalid}개 줄 제거")

    final_content = '\n'.join(final_lines)

    # 결과 저장
    print(f"[5/5] 결과 저장")
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"  출력 파일: {output_path}")
    print(f"  원본 크기: {input_file.stat().st_size:,} bytes")
    print(f"  정규화 크기: {output_file.stat().st_size:,} bytes")

    # 검증
    try:
        from rdflib import Graph
        g = Graph()
        g.parse(output_path, format='turtle')
        print(f"  ✅ TTL 검증 성공: {len(g)} 트리플")
    except ImportError:
        print(f"  ⚠️  TTL 검증 건너뜀 (rdflib 없음)")
    except Exception as e:
        print(f"  ⚠️  TTL 검증 실패: {str(e)[:100]}")
        # 실패 줄 찾기
        error_line = re.search(r'at line (\d+)', str(e))
        if error_line:
            line_num = int(error_line.group(1))
            lines = final_content.split('\n')
            print(f"  문제 줄 ({line_num}):")
            for i in range(max(0, line_num-3), min(len(lines), line_num+3)):
                marker = ">>>" if i == line_num-1 else "   "
                print(f"    {marker} {i+1}: {lines[i][:100]}")

    return uri_mapping, prop_mapping


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='TTL 파일 정규화')
    parser.add_argument('--input', '-i',
                        default='../instances/korean_history_instances.ttl',
                        help='입력 TTL 파일 경로')
    parser.add_argument('--output', '-o',
                        default='../instances/korean_history_normalized.ttl',
                        help='출력 TTL 파일 경로')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_path = script_dir / args.input if not Path(args.input).is_absolute() else Path(args.input)
    output_path = script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)

    print("=" * 60)
    print("TTL 파일 정규화")
    print("=" * 60)

    normalize_ttl_file(str(input_path), str(output_path))

    print("=" * 60)
    print("정규화 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
