#!/usr/bin/env python3
"""
중복 트리플 확인 스크립트
같은 주체-프로퍼티-객체 조합이 여러 번 나타나는지 확인
"""

import os
from collections import Counter
from rdflib import Graph, URIRef, Literal, BNode

def check_duplicates(ttl_path: str):
    """중복 트리플 확인"""
    print(f"TTL 파일 파싱 중: {ttl_path}")
    
    g = Graph()
    g.parse(ttl_path, format='turtle')
    
    # 모든 트리플을 문자열로 변환하여 카운트
    triple_strings = []
    for s, p, o in g:
        triple_str = f"{s} {p} {o}"
        triple_strings.append(triple_str)
    
    # 중복 확인
    counter = Counter(triple_strings)
    duplicates = {triple: count for triple, count in counter.items() if count > 1}
    
    print(f"\n총 트리플 수: {len(triple_strings):,}")
    print(f"고유 트리플 수: {len(counter):,}")
    print(f"중복된 트리플 수: {len(duplicates):,}")
    print(f"중복으로 인한 추가 트리플: {len(triple_strings) - len(counter):,}")
    
    if duplicates:
        print(f"\n상위 10개 중복 트리플:")
        sorted_dups = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]
        for triple, count in sorted_dups:
            print(f"  [{count}회] {triple[:100]}")
    
    # 엣지와 리터럴 분류
    edges = 0
    literals = 0
    for s, p, o in g:
        if isinstance(o, URIRef) or isinstance(o, BNode):
            edges += 1
        elif isinstance(o, Literal):
            literals += 1
    
    print(f"\n엣지 수 (URI/BNode 객체): {edges:,}")
    print(f"리터럴 속성 수: {literals:,}")
    print(f"합계: {edges + literals:,}")
    print(f"총 트리플과의 차이: {len(triple_strings) - (edges + literals):,}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ttl_file = os.path.join(script_dir, "..", "instances", "korean_history_normalized.ttl")
    
    if not os.path.exists(ttl_file):
        print(f"❌ TTL 파일이 없습니다: {ttl_file}")
        exit(1)
    
    check_duplicates(ttl_file)

