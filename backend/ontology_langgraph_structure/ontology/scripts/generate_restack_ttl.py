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


def save_restack_file(restack_path: str, remaining_rows: list):
    """
    .restack 파일에 남은 행 번호만 저장
    
    Args:
        restack_path: .restack 파일 경로
        remaining_rows: 남은 행 번호 리스트
    """
    try:
        with open(restack_path, 'w', encoding='utf-8') as f:
            for row_num in sorted(remaining_rows):
                f.write(f"{row_num}\n")
    except Exception as e:
        print(f"    ⚠️ .restack 파일 업데이트 중 오류: {e}")


def generate_restack_ttl(restack_rows: list, csv_path: str, output_dir: str, restack_path: str, part_number: int = None):
    """
    .restack 파일에 지정된 행들만 TTL로 변환
    
    Args:
        restack_rows: 처리할 행 번호 리스트 (1-based, CSV 헤더 제외)
        csv_path: CSV 파일 경로
        output_dir: TTL 출력 디렉토리
        restack_path: .restack 파일 경로 (처리된 항목 삭제용)
        part_number: 파트 번호 (병렬 실행 시 사용, None이면 기본 파일 사용)
    """
    if not restack_rows:
        print("⚠️ 처리할 행이 없습니다.")
        return
    
    print(f"📋 처리할 행: {len(restack_rows)}개")
    if len(restack_rows) <= 10:
        print(f"   행 번호: {restack_rows}")
    else:
        print(f"   행 번호: {restack_rows[:5]} ... {restack_rows[-5:]}")
    print()
    
    # 생성기 초기화
    generator = LLMTTLGenerator(csv_path, output_dir)
    
    # 출력 파일 경로 (파트 번호가 있으면 별도 파일, 없으면 기본 파일)
    if part_number:
        output_path = os.path.join(output_dir, f"korean_history_instances_2_part{part_number}.ttl")
    else:
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
    
    # 배치 저장 설정
    BATCH_SIZE = 50  # 50개마다 저장
    
    # 배치 저장용 버퍼
    batch_triples = []
    processed_count = 0
    error_count = 0
    
    # 처리된 행 번호 추적 (set으로 관리하여 빠른 조회)
    remaining_rows = set(restack_rows)  # 남은 행 번호들
    processed_in_batch = []  # 현재 배치에서 처리된 행 번호들
    
    try:
        # CSV 읽기 (BOM 처리)
        with open(csv_path, 'r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for i, row in enumerate(reader, 1):  # 1-based 인덱스
                # .restack에 있는 행만 처리
                if i not in remaining_rows:
                    continue
                
                print(f"  처리 중: {i}. {row['title']}")
                
                try:
                    # 트리플 생성
                    triples = generator.process_csv_row(row)
                    
                    # 배치에 추가
                    if triples:
                        batch_triples.append(f"\n# {row['title']} ({row['category']}) ")
                        batch_triples.extend(triples)
                        batch_triples.append("")
                    
                    processed_count += 1
                    processed_in_batch.append(i)  # 처리된 행 번호 기록
                    
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
                    # 에러가 발생해도 처리된 것으로 간주하고 .restack에서 제거
                    processed_in_batch.append(i)
                
                # 50개마다 배치 저장 및 .restack 파일 업데이트
                if processed_count % BATCH_SIZE == 0 and batch_triples:
                    try:
                        # TTL 파일에 저장
                        with open(output_path, 'a', encoding='utf-8') as f:
                            f.write("\n".join(batch_triples))
                        batch_triples = []
                        
                        # 처리된 항목들을 .restack에서 제거
                        for processed_row in processed_in_batch:
                            remaining_rows.discard(processed_row)
                        
                        # .restack 파일 업데이트
                        save_restack_file(restack_path, list(remaining_rows))
                        
                        print(f"    💾 배치 저장 완료 ({processed_count}개 처리됨)")
                        print(f"    📝 .restack 파일 업데이트 완료 (남은 항목: {len(remaining_rows)}개)")
                        
                        # 배치 처리된 항목 리스트 초기화
                        processed_in_batch = []
                        
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
                
                # 처리된 항목들을 .restack에서 제거
                for processed_row in processed_in_batch:
                    remaining_rows.discard(processed_row)
                save_restack_file(restack_path, list(remaining_rows))
                print(f"📝 .restack 파일 업데이트 완료 (남은 항목: {len(remaining_rows)}개)")
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
                
                # 처리된 항목들을 .restack에서 제거
                for processed_row in processed_in_batch:
                    remaining_rows.discard(processed_row)
                save_restack_file(restack_path, list(remaining_rows))
                print(f"📝 .restack 파일 업데이트 완료 (남은 항목: {len(remaining_rows)}개)")
            except:
                pass
        raise
    finally:
        # 남은 배치 저장 및 .restack 파일 최종 업데이트
        if batch_triples:
            try:
                with open(output_path, 'a', encoding='utf-8') as f:
                    f.write("\n".join(batch_triples))
                
                # 처리된 항목들을 .restack에서 제거
                for processed_row in processed_in_batch:
                    remaining_rows.discard(processed_row)
                save_restack_file(restack_path, list(remaining_rows))
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
    import argparse
    
    # 커맨드라인 인자 파싱
    parser = argparse.ArgumentParser(description='.restack 파일 기반 TTL 재생성')
    parser.add_argument('--restack-file', type=str, help='.restack 파일 경로 (기본값: instances/.restack)')
    parser.add_argument('--part-number', type=int, help='파트 번호 (병렬 실행 시 사용)')
    args = parser.parse_args()
    
    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    output_dir = script_dir.parent / "instances"
    
    # .restack 파일 경로 설정
    if args.restack_file:
        restack_path = Path(args.restack_file)
    else:
        restack_path = output_dir / ".restack"
    
    # 파트 번호 저장
    part_number = args.part_number if args.part_number else None
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # .restack 파일 읽기
    restack_rows = load_restack_rows(str(restack_path))
    
    if not restack_rows:
        print("⚠️ .restack 파일에 처리할 행이 없습니다.")
        print(f"   파일 경로: {restack_path}")
        return
    
    # 출력 파일명 결정
    if args.part_number:
        output_filename = f"korean_history_instances_2_part{args.part_number}.ttl"
    else:
        output_filename = "korean_history_instances_2.ttl"
    
    print("=" * 60)
    print("🚀 .restack 파일 기반 TTL 재생성 시작")
    if args.part_number:
        print(f"   파트 {args.part_number}")
    print("=" * 60)
    print(f"📂 입력 CSV: {csv_path}")
    print(f"📂 출력 TTL: {output_dir}/{output_filename}")
    print(f"📋 .restack 파일: {restack_path}")
    print()
    
    # TTL 생성
    generate_restack_ttl(restack_rows, str(csv_path), str(output_dir), str(restack_path), part_number)


if __name__ == "__main__":
    main()

