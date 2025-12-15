"""
HistoK PGVector CLI

pgvector 데이터 로딩 관리 CLI

사용법:
    pgvector_load title    - 제목 임베딩 로드
    pgvector_load contents - 문서 내용 임베딩 로드
    pgvector_load --help   - 도움말 표시
"""

import click
import subprocess
import sys
from pathlib import Path


@click.group()
@click.version_option(version='0.1.0', prog_name='pgvector_load')
def cli():
    """
    HistoK PGVector 데이터 로딩 CLI

    제목 임베딩과 문서 내용 임베딩을 pgvector 데이터베이스에 로드합니다.
    """
    pass


@cli.command()
@click.option('--batch-size', default=100, help='배치 크기 (기본값: 100)')
@click.option('--verbose', is_flag=True, help='상세 로그 출력')
def title(batch_size, verbose):
    """
    제목 임베딩을 pgvector에 로드

    TTL 파일의 엔티티 제목(rdfs:label)을 임베딩하여 pgvector에 저장합니다.

    예시:
        pgvector_load title
        pgvector_load title --batch-size 200 --verbose
    """
    click.echo("📦 제목 임베딩 로드 시작...")
    click.echo(f"   배치 크기: {batch_size}")

    script_path = Path(__file__).parent / "ETL" / "load_title_embeddings.py"

    if not script_path.exists():
        click.echo(f"❌ 오류: 스크립트를 찾을 수 없습니다: {script_path}", err=True)
        raise click.Abort()

    try:
        # 현재 실행 중인 Python 인터프리터 사용 (가상환경 보장)
        python_executable = sys.executable
        cmd = [python_executable, str(script_path)]
        if verbose:
            cmd.append("--verbose")

        # 항상 실시간 출력
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            click.echo("✅ 제목 임베딩 로드 완료!")
        else:
            click.echo("❌ 로드 실패", err=True)
            raise click.Abort()

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 오류 발생: {e}", err=True)
        if hasattr(e, 'stdout') and e.stdout:
            click.echo(f"출력:\n{e.stdout}", err=True)
        if hasattr(e, 'stderr') and e.stderr:
            click.echo(f"오류 메시지:\n{e.stderr}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ 예상치 못한 오류: {e}", err=True)
        import traceback
        click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@cli.command()
@click.option('--batch-size', default=100, help='배치 크기 (기본값: 100)')
@click.option('--verbose', is_flag=True, help='상세 로그 출력')
def contents(batch_size, verbose):
    """
    문서 내용 임베딩을 pgvector에 로드

    조선왕조실록 문서를 청크 단위로 임베딩하여 pgvector에 저장합니다.

    예시:
        pgvector_load contents
        pgvector_load contents --batch-size 50 --verbose
    """
    click.echo("📦 문서 내용 임베딩 로드 시작...")
    click.echo(f"   배치 크기: {batch_size}")

    script_path = Path(__file__).parent / "ETL" / "load_to_pgvector.py"

    if not script_path.exists():
        click.echo(f"❌ 오류: 스크립트를 찾을 수 없습니다: {script_path}", err=True)
        raise click.Abort()

    try:
        # 현재 실행 중인 Python 인터프리터 사용 (가상환경 보장)
        python_executable = sys.executable
        cmd = [python_executable, str(script_path)]
        if verbose:
            cmd.append("--verbose")

        # 항상 실시간 출력
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            click.echo("✅ 문서 내용 임베딩 로드 완료!")
        else:
            click.echo("❌ 로드 실패", err=True)
            raise click.Abort()

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 오류 발생: {e}", err=True)
        if hasattr(e, 'stdout') and e.stdout:
            click.echo(f"출력:\n{e.stdout}", err=True)
        if hasattr(e, 'stderr') and e.stderr:
            click.echo(f"오류 메시지:\n{e.stderr}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ 예상치 못한 오류: {e}", err=True)
        import traceback
        click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@cli.command()
def status():
    """
    pgvector 데이터베이스 상태 확인

    현재 저장된 임베딩 데이터 통계를 표시합니다.
    """
    click.echo("📊 PGVector 데이터베이스 상태 확인 중...")
    # TODO: 데이터베이스 연결하여 통계 표시
    click.echo("   제목 임베딩: (구현 예정)")
    click.echo("   문서 임베딩: (구현 예정)")


if __name__ == '__main__':
    cli()
