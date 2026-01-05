"""
SPARQL 쿼리 결과 캐싱

Redis를 사용하여 SPARQL 쿼리 결과를 캐싱하여 성능 향상
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any

# Redis 클라이언트 (lazy loading)
_redis_client = None
_redis_available = False


def get_redis_client():
    """Redis 클라이언트 가져오기 (lazy loading)"""
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        # SPARQL 캐시는 DB 2 사용 (Celery와 분리)
        redis_url = redis_url.rsplit("/", 1)[0] + "/2"

        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1
        )

        # 연결 테스트
        _redis_client.ping()
        _redis_available = True
        print(f"✓ SPARQL 캐싱 활성화 (Redis DB 2)")
        return _redis_client

    except Exception as e:
        print(f"⚠️ Redis 연결 실패, SPARQL 캐싱 비활성화: {e}")
        _redis_available = False
        return None


def generate_cache_key(query: str, endpoint: str = "") -> str:
    """SPARQL 쿼리 + 엔드포인트로 캐시 키 생성"""
    # 공백 정규화 (쿼리 포맷팅 차이 무시)
    normalized = " ".join(query.split())
    content = f"{endpoint}:{normalized}"
    hash_digest = hashlib.md5(content.encode()).hexdigest()
    return f"sparql:{hash_digest}"


def get_cached_sparql(query: str, endpoint: str = "") -> Optional[Dict[str, Any]]:
    """캐시에서 SPARQL 쿼리 결과 가져오기"""
    if not _redis_available:
        return None

    client = get_redis_client()
    if client is None:
        return None

    try:
        cache_key = generate_cache_key(query, endpoint)
        cached = client.get(cache_key)

        if cached:
            result = json.loads(cached)
            return result

    except Exception as e:
        print(f"  ⚠️ SPARQL 캐시 조회 실패: {e}")

    return None


def set_cached_sparql(query: str, result: Dict[str, Any], endpoint: str = "", ttl: int = 3600):
    """SPARQL 쿼리 결과를 캐시에 저장"""
    if not _redis_available:
        return False

    client = get_redis_client()
    if client is None:
        return False

    try:
        cache_key = generate_cache_key(query, endpoint)
        serialized = json.dumps(result, ensure_ascii=False)

        # TTL 설정 (기본 1시간)
        client.setex(cache_key, ttl, serialized)
        return True

    except Exception as e:
        print(f"  ⚠️ SPARQL 캐시 저장 실패: {e}")
        return False


def clear_sparql_cache():
    """SPARQL 캐시 전체 삭제 (관리용)"""
    client = get_redis_client()
    if client is None:
        return 0

    try:
        # sparql:* 패턴의 모든 키 삭제
        keys = client.keys("sparql:*")
        if keys:
            deleted = client.delete(*keys)
            print(f"✓ SPARQL 캐시 삭제: {deleted}개 키")
            return deleted
        return 0

    except Exception as e:
        print(f"⚠️ 캐시 삭제 실패: {e}")
        return 0
