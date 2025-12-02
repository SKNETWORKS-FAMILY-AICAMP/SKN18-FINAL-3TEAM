"""
API 테스트 스크립트

TTL 데이터에 확실히 있는 내용으로 API를 테스트합니다.
"""

import requests
import json
from pathlib import Path

API_URL = "http://localhost:8001"

# 테스트 쿼리들
TEST_QUERIES = {
    "basic": {
        "name": "기본 데이터 확인 (트리플 10개)",
        "rules": "all_rules.rules",
        "query": """
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
} LIMIT 10
"""
    },
    "person": {
        "name": "인물 데이터 확인",
        "rules": "person_inference.rules",
        "query": """
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?person ?label WHERE {
    ?person rdf:type hist:Person .
    ?person rdfs:label ?label .
} LIMIT 10
"""
    },
    "event": {
        "name": "사건 데이터 확인",
        "rules": "causal_inference.rules",
        "query": """
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?event ?label WHERE {
    ?event rdf:type hist:Event .
    ?event rdfs:label ?label .
} LIMIT 10
"""
    }
}


def test_api(test_name: str, test_config: dict):
    """단일 테스트 실행"""
    print(f"\n{'='*60}")
    print(f"🧪 테스트: {test_config['name']}")
    print(f"{'='*60}")
    
    payload = {
        "ontology": "korean_history.owl",
        "instances": [],
        "rules": test_config["rules"],
        "query": test_config["query"].strip()
    }
    
    try:
        print(f"📤 요청 전송 중...")
        response = requests.post(f"{API_URL}/infer", json=payload, timeout=120)
        
        print(f"📥 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 상태: {result.get('status')}")
            print(f"📊 메시지: {result.get('message')}")
            
            if "results" in result:
                bindings = result["results"].get("results", {}).get("bindings", [])
                print(f"📈 결과 개수: {len(bindings)}개")
                
                if bindings:
                    print(f"\n📋 결과 샘플 (최대 5개):")
                    for i, binding in enumerate(bindings[:5], 1):
                        # 결과 간단히 출력
                        values = [f"{k}={v.get('value', 'N/A')[:50]}" for k, v in binding.items()]
                        print(f"   {i}. {', '.join(values)}")
                else:
                    print(f"⚠️ 결과가 없습니다.")
            elif "query_error" in result:
                print(f"❌ 쿼리 에러: {result['query_error'][:200]}")
            else:
                print(f"⚠️ 결과가 응답에 없습니다.")
        else:
            print(f"❌ 에러: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   상세: {str(error_detail)[:300]}")
            except:
                print(f"   응답: {response.text[:300]}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️ 타임아웃 (120초 초과)")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


def main():
    """모든 테스트 실행"""
    print(f"🚀 API 테스트 시작")
    print(f"   API URL: {API_URL}")
    
    # 헬스체크
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code == 200:
            health_data = health.json()
            print(f"✅ API 헬스체크: {health_data.get('status')}")
        else:
            print(f"⚠️ API 헬스체크 실패: {health.status_code}")
            return
    except Exception as e:
        print(f"❌ API 연결 실패: {e}")
        print(f"   API 서버가 실행 중인지 확인하세요: python realtime_inference_api.py")
        return
    
    # 각 테스트 실행
    for test_name, test_config in TEST_QUERIES.items():
        test_api(test_name, test_config)
    
    print(f"\n{'='*60}")
    print(f"✅ 모든 테스트 완료")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
