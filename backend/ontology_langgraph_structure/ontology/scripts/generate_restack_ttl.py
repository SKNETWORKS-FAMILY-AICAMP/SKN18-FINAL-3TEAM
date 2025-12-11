"""
.restack 파일에 저장된 행 번호들만 TTL로 변환

.restack 파일 형식:
- 각 줄에 행 번호 (1-based, CSV 헤더 제외)
- 빈 줄은 무시
"""

import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv
from llm_ttl_generator import LLMTTLGenerator

# .env 파일 로드
load_dotenv()

# CSV 필드 크기 제한 증가
csv.field_size_limit(sys.maxsize)


def load_restack_rows(restack_path: str) -> list:
    """
    .restack 파일에서 행 번호 목록 읽기
    
    Args:
        restack_path: .restack 파일 경로
        
    Returns:
        행 번호 리스트 (1-based, CSV 헤더 제외)
    """
    if not os.path.exists(restack_path):
        print(f"⚠️ .restack 파일이 없습니다: {restack_path}")
        return []
    
    rows = []
    with open(restack_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and line.isdigit():
                rows.append(int(line))
    
    return sorted(set(rows))  # 중복 제거 및 정렬


def generate_restack_ttl(restack_rows: list, csv_path: str, output_dir: str):
    """
    .restack 파일에 지정된 행들만 TTL로 변환
    
    Args:
        restack_rows: 처리할 행 번호 리스트 (1-based, CSV 헤더 제외)
        csv_path: CSV 파일 경로
        output_dir: TTL 출력 디렉토리
    """
    if not restack_rows:
        print("⚠️ 처리할 행이 없습니다.")
        return
    
    print(f"📋 처리할 행: {len(restack_rows)}개")
    print(f"   행 번호: {restack_rows}")
    print()
    
    # 생성기 초기화
    generator = LLMTTLGenerator(csv_path, output_dir)
    
    # 출력 파일 경로 (ttl_2에 추가)
    output_path = os.path.join(output_dir, "korean_history_instances_2.ttl")
    
    # TTL 헤더 확인 (파일이 없으면 헤더 추가)
    if not os.path.exists(output_path):
        header = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix hist: <http://www.example.org/korean-history#> .",
            "",
            "# 조선시대 역사 인스턴스 데이터 (restack 재처리)",
            ""
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(header))
        print(f"📝 TTL 파일 생성: {os.path.basename(output_path)}")
    else:
        print(f"📝 기존 TTL 파일에 추가: {os.path.basename(output_path)}")
    
    import csv
    
    # 배치 저장용 버퍼
    batch_triples = []
    processed_count = 0
    error_count = 0
    
    try:
        # CSV 읽기 (BOM 처리)
        with open(csv_path, 'r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for i, row in enumerate(reader, 1):  # 1-based 인덱스
                # .restack에 있는 행만 처리
                if i not in restack_rows:
                    continue
                
                print(f"  처리 중: {i}. {row['title']}")
                
                try:
                    # 트리플 생성
                    triples = generator.process_csv_row(row)
                    
                    # 배치에 추가
                    if triples:
                        batch_triples.append(f"\n# {row['title']} ({row['category']}) - 재처리")
                        batch_triples.extend(triples)
                        batch_triples.append("")
                    
                    processed_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"    ❌ 에러: {e}")
                    # 에러 로그 기록
                    error_log_path = os.path.join(output_dir, "error_log.txt")
                    try:
                        with open(error_log_path, 'a', encoding='utf-8') as f:
                            f.write(f"{i}. {row['title']}: {e}\n")
                    except:
                        pass
                
                # 각 행 처리 후 즉시 저장 (데이터 손실 방지)
                if batch_triples:
                    try:
                        with open(output_path, 'a', encoding='utf-8') as f:
                            f.write("\n".join(batch_triples))
                        batch_triples = []
                        print(f"    💾 저장 완료")
                    except Exception as e:
                        print(f"    ⚠️ 저장 중 오류: {e}")
    
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨 (Ctrl+C)")
        # 진행된 내용 저장
        if batch_triples:
            try:
                with open(output_path, 'a', encoding='utf-8') as f:
                    f.write("\n".join(batch_triples))
                print("💾 중단 전까지의 진행 상황이 저장되었습니다")
            except:
                pass
        raise
    except Exception as e:
        print(f"\n❌ 치명적 오류 발생: {e}")
        # 진행된 내용 저장
        if batch_triples:
            try:
                with open(output_path, 'a', encoding='utf-8') as f:
                    f.write("\n".join(batch_triples))
                print("💾 오류 발생 전까지의 진행 상황이 저장되었습니다")
            except:
                pass
        raise
    finally:
        # 남은 배치 저장
        if batch_triples:
            try:
                with open(output_path, 'a', encoding='utf-8') as f:
                    f.write("\n".join(batch_triples))
            except:
                pass
    
    print()
    print("=" * 60)
    print(f"✅ .restack TTL 변환 완료!")
    print("=" * 60)
    print(f"   총 처리: {processed_count}개")
    print(f"   에러: {error_count}개")
    if error_count > 0:
        error_log_path = os.path.join(output_dir, "error_log.txt")
        print(f"   에러 로그: {error_log_path}")


def main():
    """메인 함수"""
    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    output_dir = script_dir.parent / "instances"
    restack_path = output_dir / ".restack"
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # .restack 파일 읽기
    restack_rows = load_restack_rows(str(restack_path))
    
    if not restack_rows:
        print("⚠️ .restack 파일에 처리할 행이 없습니다.")
        print(f"   파일 경로: {restack_path}")
        return
    
    print("=" * 60)
    print("🚀 .restack 파일 기반 TTL 재생성 시작")
    print("=" * 60)
    print(f"📂 입력 CSV: {csv_path}")
    print(f"📂 출력 TTL: {output_dir}/korean_history_instances_2.ttl")
    print(f"📋 .restack 파일: {restack_path}")
    print()
    
    # TTL 생성
    generate_restack_ttl(restack_rows, str(csv_path), str(output_dir))


if __name__ == "__main__":
    main()

