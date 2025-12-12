"""
Neo4j 노드 + 엣지 생성 파이프라인 전체 실행 스크립트
"""
import csv

from backend.db_pipeline.neo4j.ETL.neo4j_query_node import run_node_job
from backend.db_pipeline.neo4j.ETL.neo4j_query_edge2 import run_edge_job
from backend.db_pipeline.common.config import INPUT_CSV
from pathlib import Path

def run_all():
    csv_path = Path(INPUT_CSV)

    csv.field_size_limit(2_147_483_647)

    print("\n=== 1) 노드 생성 파이프라인 실행 ===")
    run_node_job(csv, csv_path)

    print("\n=== 2) 엣지 생성 파이프라인 실행 ===")
    run_edge_job(csv, csv_path)

    print("\n전체 Neo4j 그래프 빌드 완료")

if __name__ == "__main__":
    run_all()
