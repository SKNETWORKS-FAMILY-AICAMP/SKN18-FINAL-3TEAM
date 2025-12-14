"""
Fuseki TTL 업로드 스크립트 (크로스 플랫폼 Python 버전)

Windows, Mac, Linux 모두에서 실행 가능합니다.

사용법:
    python load_ttl_to_fuseki.py
    python load_ttl_to_fuseki.py --ttl-file custom.ttl
    python load_ttl_to_fuseki.py --fuseki-url http://localhost:3030 --dataset korean-history
"""

import os
import sys
import json
import requests
from pathlib import Path
import click


def get_file_size(file_path: Path) -> str:
    """파일 크기를 사람이 읽기 쉬운 형식으로 반환"""
    size_bytes = file_path.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def check_fuseki_connection(fuseki_url: str) -> bool:
    """Fuseki 서버 연결 확인"""
    try:
        response = requests.get(fuseki_url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def check_dataset_exists(fuseki_url: str, dataset: str, auth: tuple) -> bool:
    """데이터셋 존재 여부 확인"""
    try:
        response = requests.get(f"{fuseki_url}/{dataset}", auth=auth, timeout=5)
        return response.status_code != 404
    except requests.exceptions.RequestException:
        return False


def create_dataset(fuseki_url: str, dataset: str, auth: tuple) -> bool:
    """데이터셋 생성"""
    try:
        response = requests.post(
            f"{fuseki_url}/$/datasets",
            auth=auth,
            data={'dbName': dataset, 'dbType': 'tdb2'},
            timeout=10
        )
        return response.status_code in [200, 201]
    except requests.exceptions.RequestException:
        return False


def delete_all_data(fuseki_url: str, dataset: str, auth: tuple) -> bool:
    """기존 데이터 삭제"""
    try:
        response = requests.post(
            f"{fuseki_url}/{dataset}/update",
            auth=auth,
            headers={'Content-Type': 'application/sparql-update'},
            data='DROP ALL',
            timeout=30
        )
        return response.status_code in [200, 204]
    except requests.exceptions.RequestException:
        return False


def upload_ttl_file(fuseki_url: str, dataset: str, ttl_file: Path, auth: tuple) -> tuple:
    """TTL 파일 업로드"""
    try:
        with open(ttl_file, 'rb') as f:
            response = requests.post(
                f"{fuseki_url}/{dataset}/data",
                auth=auth,
                headers={'Content-Type': 'text/turtle'},
                data=f,
                timeout=300
            )
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return 0, str(e)


def count_triples(fuseki_url: str, dataset: str, auth: tuple) -> int:
    """업로드된 트리플 개수 조회"""
    try:
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"
        response = requests.post(
            f"{fuseki_url}/{dataset}/sparql",
            auth=auth,
            data={'query': query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return int(data['results']['bindings'][0]['count']['value'])
    except (requests.exceptions.RequestException, KeyError, ValueError):
        pass
    return -1


@click.command()
@click.option('--ttl-file', type=click.Path(exists=True), help='TTL 파일 경로')
@click.option('--fuseki-url', default='http://localhost:3030', help='Fuseki 서버 URL')
@click.option('--dataset', default='korean-history', help='데이터셋 이름')
@click.option('--fuseki-user', default='admin', help='Fuseki 사용자명')
@click.option('--fuseki-password', help='Fuseki 비밀번호')
def main(ttl_file, fuseki_url, dataset, fuseki_user, fuseki_password):
    """
    TTL 파일을 Apache Fuseki에 업로드 (크로스 플랫폼)

    Windows, Mac, Linux 모두에서 실행 가능합니다.
    """

    # 기본 TTL 파일 경로
    if not ttl_file:
        script_dir = Path(__file__).parent
        instances_dir = script_dir.parent / "instances"
        ttl_file = instances_dir / "korean_history_normalized.ttl"
    else:
        ttl_file = Path(ttl_file)

    # Fuseki 비밀번호 (환경변수 또는 기본값)
    if not fuseki_password:
        fuseki_password = os.getenv('FUSEKI_PASSWORD') or os.getenv('FUSEKI_ADMIN_PASSWORD') or 'fuseki1234'

    auth = (fuseki_user, fuseki_password)

    # 파일 존재 확인
    if not ttl_file.exists():
        click.echo(f"❌ ERROR: TTL 파일이 없습니다: {ttl_file}", err=True)
        sys.exit(1)

    click.echo("=" * 70)
    click.echo("Fuseki TTL 업로드 (크로스 플랫폼)")
    click.echo("=" * 70)
    click.echo(f"Fuseki URL: {fuseki_url}")
    click.echo(f"데이터셋:   {dataset}")
    click.echo(f"파일:       {ttl_file}")
    click.echo(f"파일 크기:  {get_file_size(ttl_file)}")
    click.echo("")

    # 1. Fuseki 서버 연결 확인
    click.echo("🔍 Fuseki 서버 연결 확인 중...")
    if not check_fuseki_connection(fuseki_url):
        click.echo(f"❌ ERROR: Fuseki 서버에 연결할 수 없습니다 ({fuseki_url})", err=True)
        click.echo("💡 힌트: docker-compose up -d fuseki 로 Fuseki를 시작하세요", err=True)
        sys.exit(1)

    click.echo("✅ OK: Fuseki 서버 연결 성공")
    click.echo("")

    # 2. 데이터셋 존재 확인 및 생성
    click.echo("🔍 데이터셋 확인 중...")
    if not check_dataset_exists(fuseki_url, dataset, auth):
        click.echo(f"데이터셋 '{dataset}'가 없습니다. 생성 중...")

        if create_dataset(fuseki_url, dataset, auth):
            click.echo("✅ OK: 데이터셋 생성 완료")
        else:
            click.echo("❌ ERROR: 데이터셋 생성 실패", err=True)
            sys.exit(1)
    else:
        click.echo("✅ OK: 데이터셋 존재")

    click.echo("")

    # 3. 기존 데이터 삭제
    click.echo("🗑️  기존 데이터 삭제 중...")
    if delete_all_data(fuseki_url, dataset, auth):
        click.echo("✅ OK: 기존 데이터 삭제 완료")
    else:
        click.echo("⚠️  WARNING: 기존 데이터 삭제 실패 (데이터가 없을 수 있음)")

    click.echo("")

    # 4. TTL 파일 업로드
    click.echo("📤 TTL 파일 업로드 중...")
    with click.progressbar(length=100, label='업로드 진행') as bar:
        status_code, error_text = upload_ttl_file(fuseki_url, dataset, ttl_file, auth)
        bar.update(100)

    click.echo(f"HTTP Status: {status_code}")

    if status_code in [200, 204]:
        click.echo("✅ SUCCESS: TTL 업로드 완료")
    elif status_code == 400:
        click.echo("❌ ERROR: TTL 파일 구문 오류 (400)", err=True)
        click.echo(f"오류 상세: {error_text[:500]}")
        sys.exit(1)
    elif status_code == 401:
        click.echo("❌ ERROR: 인증 실패 (401) - Fuseki 사용자명/비밀번호를 확인하세요", err=True)
        sys.exit(1)
    elif status_code == 404:
        click.echo("❌ ERROR: 데이터셋을 찾을 수 없습니다 (404)", err=True)
        sys.exit(1)
    else:
        click.echo(f"⚠️  WARNING: HTTP {status_code} - 업로드 상태 불명확")
        click.echo(f"응답: {error_text[:500]}")

    click.echo("")

    # 5. 업로드 확인 (트리플 개수 조회)
    click.echo("✔️  업로드 확인 중...")
    triple_count = count_triples(fuseki_url, dataset, auth)

    if triple_count >= 0:
        click.echo(f"✅ OK: 업로드된 트리플 개수: {triple_count:,}")
    else:
        click.echo("⚠️  WARNING: 트리플 개수 확인 실패")

    click.echo("")
    click.echo("=" * 70)
    click.echo("🎉 업로드 완료!")
    click.echo("=" * 70)


if __name__ == '__main__':
    main()
