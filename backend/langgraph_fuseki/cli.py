"""
HistoK Ontology CLI

온톨로지 및 LangGraph 관리 CLI

사용법:
    ontology ttl-load - TTL 파일을 Fuseki에 로드
    ontology main     - LangGraph Fuseki 인터랙티브 실행
    ontology --help   - 도움말 표시
"""

import click
import subprocess
import sys
from pathlib import Path


@click.group()
@click.version_option(version='0.1.0', prog_name='ontology')
def cli():
    """
    HistoK Ontology 관리 CLI

    TTL 데이터 로딩 및 LangGraph Fuseki 실행을 관리합니다.
    """
    pass


@cli.command(name='ttl-load')
@click.option('--ttl-file', type=click.Path(exists=True), help='TTL 파일 경로')
@click.option('--fuseki-url', default='http://localhost:3030', help='Fuseki 서버 URL')
@click.option('--dataset', default='korean-history', help='데이터셋 이름')
@click.option('--fuseki-user', default='admin', help='Fuseki 사용자명')
@click.option('--fuseki-password', help='Fuseki 비밀번호')
def ttl_load(ttl_file, fuseki_url, dataset, fuseki_user, fuseki_password):
    """
    TTL 파일을 Apache Fuseki에 로드 (크로스 플랫폼)

    온톨로지 데이터(korean_history_normalized.ttl)를 Fuseki 서버에 업로드합니다.
    Windows, Mac, Linux 모두에서 실행 가능합니다.

    예시:
        ontology ttl-load
        ontology ttl-load --fuseki-url http://localhost:3030 --dataset korean-history
        ontology ttl-load --ttl-file custom.ttl --fuseki-password secret
    """
    try:
        # Python 스크립트 직접 import하여 실행
        from backend.langgraph_fuseki.ontology.scripts.load_ttl_to_fuseki import main as load_main

        # Click 컨텍스트를 통해 파라미터 전달
        ctx = click.Context(load_main)
        ctx.params = {
            'ttl_file': ttl_file,
            'fuseki_url': fuseki_url,
            'dataset': dataset,
            'fuseki_user': fuseki_user,
            'fuseki_password': fuseki_password,
        }

        load_main.invoke(ctx)

    except ImportError as e:
        click.echo(f"❌ 모듈 import 실패: {e}", err=True)
        click.echo("   먼저 'uv pip install -e .'를 실행하여 패키지를 설치하세요.", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ 오류 발생: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--verbose', is_flag=True, help='상세 로그 출력')
def main(verbose):
    """
    HistoK LangGraph Fuseki 인터랙티브 실행

    조선시대 역사 질문에 답변하는 LangGraph 시스템을 시작합니다.

    예시:
        ontology main
        ontology main --verbose
    """
    click.echo("🚀 HistoK LangGraph Fuseki 시작 중...")

    try:
        # Python 모듈로 실행
        from backend.langgraph_fuseki.main import main as langgraph_main

        # 직접 main 함수 호출
        langgraph_main()

    except ImportError as e:
        click.echo(f"❌ 모듈 import 실패: {e}", err=True)
        click.echo("   먼저 'uv pip install -e .'를 실행하여 패키지를 설치하세요.", err=True)
        raise click.Abort()
    except KeyboardInterrupt:
        click.echo("\n\n👋 프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ 오류 발생: {e}", err=True)
        raise click.Abort()


@cli.command()
def status():
    """
    Fuseki 서버 및 온톨로지 데이터 상태 확인

    Fuseki 서버 연결 상태와 데이터셋 통계를 표시합니다.
    """
    click.echo("📊 Fuseki 서버 상태 확인 중...")

    try:
        import requests
        from backend.langgraph_fuseki.config import FUSEKI_URL

        # Fuseki 서버 ping
        response = requests.get(f"{FUSEKI_URL}/$/ping", timeout=5)

        if response.status_code == 200:
            click.echo(f"✅ Fuseki 서버 연결: {FUSEKI_URL}")

            # 데이터셋 통계 (SPARQL COUNT 쿼리)
            query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
            sparql_url = f"{FUSEKI_URL}/query"

            response = requests.post(
                sparql_url,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                count = result['results']['bindings'][0]['count']['value']
                click.echo(f"   총 트리플 수: {count}")
            else:
                click.echo("   ⚠️  데이터셋 통계 조회 실패")
        else:
            click.echo(f"❌ Fuseki 서버 연결 실패: {FUSEKI_URL}", err=True)

    except ImportError:
        click.echo("❌ requests 라이브러리가 필요합니다: pip install requests", err=True)
    except Exception as e:
        click.echo(f"❌ 오류 발생: {e}", err=True)
        click.echo("   Fuseki 서버가 실행 중인지 확인하세요.", err=True)


if __name__ == '__main__':
    cli()
