#!/usr/bin/env python3
"""
TTL 파일에서 직접 통계 계산
- 총 트리플 수
- 노드 수 (고유 주체 및 객체)
- 엣지 수 (객체가 리터럴이 아닌 트리플)
- 프로퍼티 수

rdflib를 사용한 정확한 파싱과 간단한 파싱 두 가지 방법 제공

rdflib 기능:
- RDF 데이터 파싱: Turtle, RDF/XML, N3, JSON-LD 등 다양한 형식 지원
- RDF 그래프 조작: 트리플 추가/삭제/수정, 그래프 병합
- SPARQL 쿼리: 로컬 RDF 그래프에서 SPARQL 쿼리 실행
- RDF 직렬화: 다양한 형식으로 RDF 데이터 저장
- 네임스페이스 관리: URI 접두사 관리 및 축약
- 검증: RDF 데이터 문법 검증
"""

import os
import sys
import re
from collections import defaultdict
from typing import Set, Dict

# rdflib 사용 시도
try:
    from rdflib import Graph, URIRef, Literal, BNode
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False

def parse_ttl_file(ttl_path: str, quiet: bool = False) -> Dict:
    """TTL 파일을 파싱하여 통계 수집"""
    stats = {
        'triples': 0,
        'subjects': set(),  # 고유 주체
        'objects_uri': set(),  # URI 객체 (엣지의 끝점)
        'predicates': set(),  # 프로퍼티
        'literals': 0,  # 리터럴 값
        'edges': 0,  # 객체가 URI인 트리플 (엣지)
    }
    
    if not quiet:
        print(f"TTL 파일 파싱 중: {ttl_path}")
    
    with open(ttl_path, 'r', encoding='utf-8') as f:
        line_num = 0
        for line in f:
            line_num += 1
            if not quiet and line_num % 10000 == 0:
                print(f"  처리 중... {line_num:,} 줄")
            
            # 주석 및 빈 줄 제외
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 세미콜론으로 끝나는 줄은 다음 줄과 연결될 수 있음
            # 간단한 파싱: 주체-프로퍼티-객체 패턴 찾기
            # TTL 형식: subject predicate object .
            # 또는: subject predicate1 object1 ; predicate2 object2 .
            
            # 주체 추출 (첫 번째 단어, 보통 URI)
            parts = line.split()
            if len(parts) < 3:
                continue
            
            subject = parts[0]
            
            # 주체가 URI인지 확인 (hist: 또는 http://로 시작)
            if subject.startswith('hist:') or subject.startswith('http://') or subject.startswith('<'):
                # 주체 정규화
                if subject.startswith('<') and subject.endswith('>'):
                    subject = subject[1:-1]
                stats['subjects'].add(subject)
            
            # 트리플 파싱 (간단한 버전)
            # predicate object 패턴 찾기
            i = 1
            while i < len(parts):
                if parts[i] == '.':
                    break
                if parts[i] == ';':
                    i += 1
                    continue
                
                predicate = parts[i]
                if i + 1 < len(parts):
                    obj = parts[i + 1]
                    
                    # 프로퍼티 추가
                    if predicate.startswith('hist:') or predicate.startswith('http://') or predicate.startswith('rdfs:') or predicate.startswith('rdf:'):
                        stats['predicates'].add(predicate)
                    
                    # 객체 확인
                    if obj.endswith(';') or obj.endswith('.'):
                        obj = obj.rstrip(';.')
                    
                    # 리터럴인지 URI인지 확인
                    if obj.startswith('"') or obj.startswith("'"):
                        # 리터럴
                        stats['literals'] += 1
                    elif obj.startswith('hist:') or obj.startswith('http://') or (obj.startswith('<') and obj.endswith('>')):
                        # URI 객체
                        obj_clean = obj
                        if obj_clean.startswith('<') and obj_clean.endswith('>'):
                            obj_clean = obj_clean[1:-1]
                        stats['objects_uri'].add(obj_clean)
                        stats['edges'] += 1
                    
                    stats['triples'] += 1
                    i += 2
                else:
                    break
    
    return stats

def parse_ttl_with_rdflib(ttl_path: str, quiet: bool = False) -> Dict:
    """rdflib를 사용한 정확한 TTL 파싱"""
    if not quiet:
        print(f"TTL 파일 파싱 중 (rdflib 사용): {ttl_path}")
    
    g = Graph()
    g.parse(ttl_path, format='turtle')
    
    stats = {
        'triples': len(g),
        'subjects': set(),
        'objects_uri': set(),
        'predicates': set(),
        'literals': 0,
        'edges': 0,
    }
    
    for s, p, o in g:
        # 주체
        if isinstance(s, URIRef):
            stats['subjects'].add(str(s))
        elif isinstance(s, BNode):
            stats['subjects'].add(f"bnode:{s}")
        
        # 프로퍼티
        if isinstance(p, URIRef):
            stats['predicates'].add(str(p))
        
        # 객체
        if isinstance(o, URIRef):
            stats['objects_uri'].add(str(o))
            stats['edges'] += 1
        elif isinstance(o, Literal):
            stats['literals'] += 1
        elif isinstance(o, BNode):
            stats['objects_uri'].add(f"bnode:{o}")
            stats['edges'] += 1
    
    return stats

def get_ttl_stats(ttl_file: str, quiet: bool = False) -> Dict:
    """TTL 파일 통계 계산 (간단한 출력 모드)"""
    if not os.path.exists(ttl_file):
        if not quiet:
            print(f"❌ TTL 파일이 없습니다: {ttl_file}")
        return None
    
    # TTL 파싱 (rdflib 우선, 없으면 간단한 파싱)
    if RDFLIB_AVAILABLE:
        try:
            stats = parse_ttl_with_rdflib(ttl_file, quiet=quiet)
        except Exception as e:
            if not quiet:
                print(f"⚠️ rdflib 파싱 실패: {e}")
            stats = parse_ttl_file(ttl_file, quiet=quiet)
    else:
        stats = parse_ttl_file(ttl_file, quiet=quiet)
    
    return stats

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TTL 파일 통계 계산')
    parser.add_argument('--ttl', type=str, help='TTL 파일 경로 (기본값: korean_history_normalized.ttl)')
    parser.add_argument('--quiet', action='store_true', help='간단한 출력만 (노드/엣지 수만)')
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.ttl:
        ttl_file = args.ttl
    else:
        ttl_file = os.path.join(script_dir, "..", "instances", "korean_history_normalized.ttl")
    
    if not os.path.exists(ttl_file):
        print(f"❌ TTL 파일이 없습니다: {ttl_file}")
        sys.exit(1)
    
    if args.quiet:
        # 간단한 출력 모드
        stats = get_ttl_stats(ttl_file, quiet=True)
        if stats:
            total_nodes = len(stats['subjects'] | stats['objects_uri'])
            print(f"노드 수: {total_nodes:,}")
            print(f"엣지 수: {stats['edges']:,}")
        sys.exit(0)
    
    # 상세 출력 모드
    file_size = os.path.getsize(ttl_file)
    print("=" * 60)
    print("TTL 파일 통계 분석")
    print("=" * 60)
    print(f"파일: {ttl_file}")
    print(f"크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    with open(ttl_file, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f)
    print(f"줄 수: {line_count:,}")
    print()
    
    # TTL 파싱
    if RDFLIB_AVAILABLE:
        try:
            stats = parse_ttl_with_rdflib(ttl_file, quiet=False)
            print("✅ rdflib를 사용한 정확한 파싱 완료")
        except Exception as e:
            print(f"⚠️ rdflib 파싱 실패: {e}")
            print("간단한 파싱 방법으로 전환...")
            stats = parse_ttl_file(ttl_file, quiet=False)
    else:
        print("⚠️ rdflib가 설치되지 않음. 간단한 파싱 방법 사용")
        stats = parse_ttl_file(ttl_file, quiet=False)
    
    print()
    print("=" * 60)
    print("통계 결과")
    print("=" * 60)
    print(f"총 트리플 수: {stats['triples']:,}")
    print(f"총 노드 수 (고유 주체): {len(stats['subjects']):,}")
    print(f"총 노드 수 (고유 객체 URI): {len(stats['objects_uri']):,}")
    total_nodes = len(stats['subjects'] | stats['objects_uri'])
    print(f"총 고유 노드 수 (주체 + 객체): {total_nodes:,}")
    print(f"총 엣지 수 (객체가 URI인 트리플): {stats['edges']:,}")
    print(f"리터럴 속성 수: {stats['literals']:,}")
    print(f"총 프로퍼티 수: {len(stats['predicates']):,}")
    print()
    
    # 비율 계산
    if stats['triples'] > 0:
        print("=" * 60)
        print("비율")
        print("=" * 60)
        print(f"엣지 비율: {stats['edges']/stats['triples']*100:.1f}%")
        print(f"리터럴 비율: {stats['literals']/stats['triples']*100:.1f}%")
        print(f"줄 수 대비 트리플 비율: {stats['triples']/line_count:.2f}")
    
    # 상위 프로퍼티 출력
    print()
    print("=" * 60)
    print("프로퍼티 목록 (일부)")
    print("=" * 60)
    sorted_props = sorted(stats['predicates'])
    for prop in sorted_props[:20]:
        print(f"  - {prop}")
    if len(sorted_props) > 20:
        print(f"  ... 외 {len(sorted_props) - 20}개")

if __name__ == "__main__":
    main()

