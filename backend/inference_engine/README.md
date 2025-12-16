# Inference Engine (추론 엔진)

## 개요
HistoK 프로젝트의 추론 엔진 - 룰셋 기반 사전 추론 시스템

**상태:** 2차 개발 예정 (현재 비활성)

## 목적
실시간 추론이 아닌, 사전에 정의된 룰셋(ruleset)을 기반으로 엣지를 생성하고 TTL 파일을 업데이트합니다.

## 구조

```
inference_engine/
├── reasoner/              # Java 기반 추론 엔진
│   ├── src/
│   ├── pom.xml
│   └── run_reasoner.sh
│
└── rules/                 # 추론 룰셋 정의
    ├── all_rules.rules
    ├── causal_inference.rules
    ├── motive_inference.rules
    ├── pattern_inference.rules
    ├── person_inference.rules
    └── temporal_inference.rules
```

## 개발 계획 (2차)

1. **룰셋 정의**
   - 인과관계 추론 규칙
   - 시간적 관계 추론 규칙
   - 패턴 기반 추론 규칙

2. **엣지 생성기**
   - 룰셋 기반 자동 트리플 생성
   - 신뢰도 점수 계산

3. **TTL 업데이트**
   - 기존 TTL 파일에 추론된 트리플 추가
   - 버전 관리 및 롤백

## 현재 상태
- reasoner 및 rules 폴더는 `backend/ontology_langgraph_structure/ontology/`에서 이동됨
- 추후 개발 시 이 폴더를 활성화하여 사용 예정

## 참고
- LangGraph Fuseki: `backend/langgraph_fuseki/`
- 온톨로지 데이터: `backend/langgraph_fuseki/ontology/instances/`
