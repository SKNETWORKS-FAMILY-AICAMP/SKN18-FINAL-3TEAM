"""
Fuseki SPARQL 클라이언트 유틸리티

문제: requests 라이브러리의 Keep-Alive로 인한 Fuseki lock 누적
해결: Connection: close 헤더 + 명시적 세션 관리
"""

import requests
from typing import Optional, Dict, Any


def execute_sparql_query(
    fuseki_url: str,
    sparql_query: str,
    timeout: int = 5,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Fuseki SPARQL 쿼리 실행 (Connection 명시적 close)

    Args:
        fuseki_url: Fuseki 엔드포인트 URL (예: http://localhost:3030/korean-history)
        sparql_query: SPARQL 쿼리 문자열
        timeout: 타임아웃 (초)
        headers: 추가 헤더

    Returns:
        SPARQL 결과 JSON 또는 None (실패 시)

    Notes:
        - Connection: close 헤더를 추가하여 Keep-Alive 방지
        - 각 요청마다 새로운 연결 생성 및 종료
        - Fuseki의 "Maximum lock count exceeded" 에러 방지
    """
    default_headers = {
        "Accept": "application/sparql-results+json",
        "Connection": "close"  # Keep-Alive 비활성화
    }

    if headers:
        default_headers.update(headers)

    try:
        response = requests.post(
            f"{fuseki_url}/sparql",
            data={"query": sparql_query},
            headers=default_headers,
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()
        else:
            # 500 에러 등
            return None

    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None
    finally:
        # 명시적으로 연결 닫기
        try:
            response.close()
        except:
            pass


def execute_sparql_update(
    fuseki_url: str,
    sparql_update: str,
    timeout: int = 10
) -> bool:
    """
    Fuseki SPARQL UPDATE 실행

    Args:
        fuseki_url: Fuseki 엔드포인트 URL
        sparql_update: SPARQL UPDATE 문자열
        timeout: 타임아웃 (초)

    Returns:
        성공 여부 (True/False)
    """
    headers = {
        "Content-Type": "application/sparql-update",
        "Connection": "close"
    }

    try:
        response = requests.post(
            f"{fuseki_url}/update",
            data=sparql_update,
            headers=headers,
            timeout=timeout
        )

        return response.status_code in (200, 204)

    except:
        return False
    finally:
        try:
            response.close()
        except:
            pass
