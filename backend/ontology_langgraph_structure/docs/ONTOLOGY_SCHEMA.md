# 조선시대 역사 온톨로지 스키마 (Korean History Ontology)

> **버전:** 2.0.0  
> **네임스페이스:** `http://www.example.org/korean-history#`  
> **Prefix:** `hist:`

---

## 📊 개요

이 온톨로지는 조선시대 역사 데이터를 구조화하기 위해 설계되었습니다. TTL(Turtle) 인스턴스 데이터에서 추출된 실제 사용 패턴을 기반으로 클래스와 프로퍼티를 정의합니다.

### 통계 (TTL 기준)

| 클래스      | 인스턴스 수 | 설명              |
| ----------- | ----------- | ----------------- |
| Person      | 106,122     | 역사적 인물       |
| Event       | 63,947      | 역사적 사건       |
| Institution | 60,067      | 제도/기관         |
| Document    | 9,098       | 문헌              |
| Nation      | 6,809       | 국가              |
| Place       | 1,769       | 장소              |
| Battle      | 1,446       | 전투 (Event 하위) |
| Policy      | 1,028       | 정책 (Event 하위) |
| Object      | 8           | 물품              |
| Role        | 4           | 역할              |
| SocialClass | 4           | 사회계층          |

---

## 🏛️ 클래스 계층 구조

```
owl:Thing
├── Person (인물)
├── Event (사건)
│   ├── Battle (전투)
│   └── Policy (정책)
├── Institution (제도/기관)
├── Document (문헌)
├── Nation (국가)
├── Place (장소)
├── Object (물품)
├── Role (역할)
└── SocialClass (사회계층)
```

---

## 📦 클래스 정의

### 1. Person (인물)

- **URI:** `hist:Person`
- **설명:** 역사적 인물 (왕, 신하, 학자, 장군 등)
- **인스턴스 예시:** `hist:Person_정조`, `hist:Person_이순신`, `hist:Person_세종`

### 2. Event (사건)

- **URI:** `hist:Event`
- **설명:** 역사적 사건 (환국, 사화, 전쟁 등)
- **인스턴스 예시:** `hist:Event_갑술환국`, `hist:Event_임진왜란`

### 3. Battle (전투)

- **URI:** `hist:Battle`
- **상위 클래스:** Event
- **설명:** 전투/해전
- **인스턴스 예시:** `hist:Battle_명량해전`, `hist:Battle_행주대첩`

### 4. Policy (정책)

- **URI:** `hist:Policy`
- **상위 클래스:** Event
- **설명:** 국가 정책 (대동법, 균역법 등)
- **인스턴스 예시:** `hist:Policy_대동법`, `hist:Policy_균역법`

### 5. Institution (제도/기관)

- **URI:** `hist:Institution`
- **설명:** 국가 제도 및 기관 (집현전, 의금부, 당파 등)
- **인스턴스 예시:** `hist:Institution_서인`, `hist:Institution_남인`, `hist:Institution_집현전`

### 6. Document (문헌)

- **URI:** `hist:Document`
- **설명:** 역사적 문헌 (실록, 의궤, 고서 등)
- **인스턴스 예시:** `hist:Document_조선왕조실록`

### 7. Nation (국가)

- **URI:** `hist:Nation`
- **설명:** 국가
- **인스턴스 예시:** `hist:Nation_조선`, `hist:Nation_명`, `hist:Nation_청`

### 8. Place (장소)

- **URI:** `hist:Place`
- **설명:** 지리적 장소
- **인스턴스 예시:** `hist:Place_경복궁`, `hist:Place_종묘`

### 9. Object (물품)

- **URI:** `hist:Object`
- **설명:** 역사적 물품 (형구, 의복, 무기 등)
- **인스턴스 예시:** `hist:Object_추`, `hist:Object_질`

### 10. Role (역할)

- **URI:** `hist:Role`
- **설명:** 인물의 역할 (관직, 직책 등)
- **인스턴스 예시:** `hist:Role_가수`

### 11. SocialClass (사회계층)

- **URI:** `hist:SocialClass`
- **설명:** 사회 계층
- **인스턴스 예시:** `hist:SocialClass_양반`

---

## 🔗 Object Properties (객체 속성)

### 참여/관계 그룹

| 프로퍼티           | 사용 빈도 | 설명                                    |
| ------------------ | --------- | --------------------------------------- |
| `participatesIn`   | 12,751    | 인물이 사건에 참여하다                  |
| `affiliatedWith`   | 11,791    | 인물/기관이 국가/당파에 소속되다        |
| `contemporaryWith` | 1,168     | 인물이 다른 인물과 동시대를 살다 (대칭) |
| `servedUnder`      | 1,047     | 인물이 다른 인물(군주) 아래에서 섬기다  |
| `attendedBy`       | 4         | 사건에 참석한 인물                      |

### 학문/교육 그룹

| 프로퍼티    | 사용 빈도 | 설명                        |
| ----------- | --------- | --------------------------- |
| `authored`  | 1,258     | 인물이 문헌을 저술하다      |
| `studentOf` | 921       | 인물이 다른 인물의 제자이다 |
| `teacherOf` | 203       | 인물이 다른 인물의 스승이다 |
| `compiled`  | 613       | 인물이 문헌을 편찬하다      |

### 인과관계 그룹

| 프로퍼티      | 사용 빈도 | 설명                                   |
| ------------- | --------- | -------------------------------------- |
| `leadsTo`     | 928       | 사건이 다른 사건으로 이어지다 (전이적) |
| `causes`      | 77        | 원인이 되다                            |
| `ledTo`       | 5         | 사건이 다른 사건으로 이어지다 (과거형) |
| `derivedFrom` | 3         | ~에서 유래하다                         |

### 설립/제도 그룹

| 프로퍼티        | 사용 빈도 | 설명                             |
| --------------- | --------- | -------------------------------- |
| `establishedBy` | 326       | 제도/기관이 인물에 의해 설립되다 |
| `initiatedBy`   | 175       | 정책이 인물에 의해 시작되다      |
| `reformed`      | 141       | 인물이 제도를 개혁하다           |
| `founded`       | 138       | 인물이 기관을 설립하다           |

### 전투/지휘 그룹

| 프로퍼티     | 사용 빈도 | 설명                   |
| ------------ | --------- | ---------------------- |
| `commands`   | 239       | 인물이 전투를 지휘하다 |
| `supervises` | 4         | 감독하다               |

### 부분/포함 그룹

| 프로퍼티            | 사용 빈도 | 설명                  |
| ------------------- | --------- | --------------------- |
| `partOf`            | 239       | ~의 일부이다 (전이적) |
| `hasPart`           | 3         | 부분을 갖다           |
| `contains`          | -         | 포함하다              |
| `includesPositions` | 6         | 직위를 포함하다       |

### 장소/위치 그룹

| 프로퍼티       | 사용 빈도 | 설명           |
| -------------- | --------- | -------------- |
| `hasLocation`  | 293       | 위치를 갖다    |
| `storedAt`     | 2         | ~에 보관되다   |
| `originatedIn` | 2         | ~에서 유래하다 |
| `heldAt`       | 2         | ~에서 개최되다 |

### 문서/기록 그룹

| 프로퍼티         | 사용 빈도 | 설명            |
| ---------------- | --------- | --------------- |
| `documents`      | 6         | 기록하다        |
| `documentsEvent` | 4         | 사건을 기록하다 |
| `records`        | 2         | 기록하다        |
| `lists`          | 2         | 목록에 포함하다 |

---

## 📊 Data Properties (데이터 속성)

### 연도/날짜 그룹 (가장 많이 사용)

| 프로퍼티          | 사용 빈도 | 타입    | 설명          |
| ----------------- | --------- | ------- | ------------- |
| `hasYear`         | 16,903    | integer | 연도          |
| `hasBirthYear`    | 451       | integer | 출생년도      |
| `hasDeathYear`    | 1,048     | integer | 사망년도      |
| `hasStartYear`    | 622       | integer | 시작년도      |
| `hasEndYear`      | 521       | integer | 종료년도      |
| `hasReignStart`   | -         | integer | 재위 시작년도 |
| `hasReignEnd`     | -         | integer | 재위 종료년도 |
| `hasCreationYear` | 3         | integer | 제작년도      |
| `occurredInYear`  | 5         | integer | 발생년도      |
| `executedInYear`  | -         | integer | 처형년도      |

### 인물 속성 그룹

| 프로퍼티         | 사용 빈도 | 타입   | 설명           |
| ---------------- | --------- | ------ | -------------- |
| `hasRank`        | 16,522    | string | 직위/관직/품계 |
| `hasAchievement` | 7,614     | string | 업적           |
| `hasField`       | 4,013     | string | 학문 분야      |
| `hasMotive`      | 1,444     | string | 동기           |
| `hasAlias`       | 22        | string | 별칭           |
| `hasTitle`       | -         | string | 작위/칭호      |

### 기관/제도 속성 그룹

| 프로퍼티           | 사용 빈도 | 타입   | 설명      |
| ------------------ | --------- | ------ | --------- |
| `hasFunction`      | 6,553     | string | 기능/역할 |
| `hasPurpose`       | 1,851     | string | 목적      |
| `hasFocusTopics`   | 6         | string | 주요 주제 |
| `hasStaffCountFor` | 7         | string | 인원 구성 |

### 문서/문헌 속성 그룹

| 프로퍼티         | 사용 빈도 | 타입   | 설명                 |
| ---------------- | --------- | ------ | -------------------- |
| `description`    | 23        | string | 설명                 |
| `hasDescription` | 5         | string | 설명을 갖다          |
| `hasSummary`     | 4         | string | 요약                 |
| `hasFormat`      | 3         | string | 형식                 |
| `hasDimensions`  | 3         | string | 크기                 |
| `hasDesignation` | 3         | string | 지정 (보물, 국보 등) |
| `notes`          | 3         | string | 참고사항             |

---

## 📁 프로퍼티 그룹 (property_groups.json)

TTL에서 사용되는 203개 프로퍼티가 50개 그룹으로 분류되어 있습니다:

```
총 프로퍼티: 203개
총 그룹: 50개
```

### 주요 그룹

| 그룹명   | 프로퍼티 수 | 예시 프로퍼티                             |
| -------- | ----------- | ----------------------------------------- |
| 문서     | 24          | documents, description, hasSummary        |
| 속성     | 22          | hasAlias, hasCategory, hasWeight          |
| 연결관계 | 21          | affiliatedWith, involves, pairedWith      |
| 연도     | 8           | hasYear, hasCreationYear, occurredInYear  |
| 인과관계 | 6           | caused, causes, leadsTo, ledTo            |
| 참여     | 3           | attendedBy, involved, participatesIn      |
| 재위     | 5           | duringReignOf, hasReignStart, hasReignEnd |

---

## 🔄 URI 네이밍 규칙

### 클래스 인스턴스 URI 패턴

```
hist:{ClassName}_{Label}
```

예시:

- `hist:Person_정조` - 인물 "정조"
- `hist:Event_갑술환국` - 사건 "갑술환국"
- `hist:Institution_서인` - 기관 "서인"
- `hist:Place_경복궁` - 장소 "경복궁"

### 라벨 (rdfs:label)

모든 인스턴스는 한글 라벨을 가집니다:

```turtle
hist:Person_정조 rdfs:label "정조" .
```

---

## 📜 TTL 인스턴스 예시

### 인물 (Person)

```turtle
hist:Person_정조 rdf:type hist:Person .
hist:Person_정조 rdfs:label "정조" .
hist:Person_정조 hist:hasReignStart 1776 .
hist:Person_정조 hist:hasReignEnd 1800 .
hist:Person_정조 hist:hasAchievement "탕평책 실시" .
hist:Person_정조 hist:hasField "성리학" .
```

### 사건 (Event)

```turtle
hist:Event_갑술환국 rdf:type hist:Event .
hist:Event_갑술환국 rdfs:label "갑술환국" .
hist:Event_갑술환국 hist:hasYear 1694 .
hist:Event_갑술환국 hist:description "1694년 숙종 20년에 서인이 재집권한 정치적 변동" .
hist:Event_갑술환국 hist:restoredPowerTo hist:Institution_서인 .
hist:Event_갑술환국 hist:ledTo hist:Event_보사공신복훈 .
```

### 기관/당파 (Institution)

```turtle
hist:Institution_서인 rdf:type hist:Institution .
hist:Institution_서인 rdfs:label "서인" .
hist:Institution_서인 hist:description "조선시대 정치적 당파(서인)" .
```

### 문헌 (Document/Institution)

```turtle
hist:Institution_20공신회맹축보사공신녹훈후 rdf:type hist:Institution .
hist:Institution_20공신회맹축보사공신녹훈후 rdfs:label "20공신회맹축 - 보사공신녹훈후" .
hist:Institution_20공신회맹축보사공신녹훈후 hist:hasCreationYear 1694 .
hist:Institution_20공신회맹축보사공신녹훈후 hist:hasSummary "1694년 갑술환국으로..." .
hist:Institution_20공신회맹축보사공신녹훈후 hist:hasDesignation "국보(2021-02)" .
hist:Institution_20공신회맹축보사공신녹훈후 hist:isStoredAt hist:Institution_한국학중앙연구원 .
```

---

## 🔍 SPARQL 쿼리 예시

### 1. 특정 인물이 참여한 사건 조회

```sparql
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?event ?eventLabel ?year WHERE {
  ?person rdfs:label "정조" .
  ?person hist:participatesIn ?event .
  ?event rdfs:label ?eventLabel .
  OPTIONAL { ?event hist:hasYear ?year }
}
```

### 2. 인과관계 체인 조회

```sparql
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?cause ?causeLabel ?effect ?effectLabel WHERE {
  ?cause hist:leadsTo ?effect .
  ?cause rdfs:label ?causeLabel .
  ?effect rdfs:label ?effectLabel .
} LIMIT 100
```

### 3. 특정 당파 소속 인물 조회

```sparql
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?person ?personLabel WHERE {
  ?institution rdfs:label "서인" .
  ?person hist:affiliatedWith ?institution .
  ?person rdfs:label ?personLabel .
} LIMIT 50
```

### 4. 스승-제자 관계 조회

```sparql
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?teacher ?teacherLabel ?student ?studentLabel WHERE {
  ?student hist:studentOf ?teacher .
  ?teacher rdfs:label ?teacherLabel .
  ?student rdfs:label ?studentLabel .
} LIMIT 50
```

### 5. 라벨 기반 엔티티 검색

```sparql
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?type ?label WHERE {
  ?entity rdfs:label ?label .
  ?entity rdf:type ?type .
  FILTER(CONTAINS(?label, "환국"))
} LIMIT 20
```

---

## ⚠️ 설계 특징 및 고려사항

### 1. 동적 프로퍼티 확장

- OWL에 정의되지 않은 프로퍼티도 TTL에서 사용 가능
- `property_groups.json`에서 동적으로 프로퍼티 그룹 관리
- 새로운 프로퍼티 추가 시 OWL 수정 불필요

### 2. 유연한 타입 시스템

- 일부 문헌이 `Institution`으로 분류됨 (공신회맹축 등)
- 정책(`Policy`)이 물품 정보를 포함하기도 함
- 실제 데이터의 복잡성을 반영한 유연한 설계

### 3. Fuseki 호환성

- OWL 없이도 TTL만으로 Fuseki 삽입 가능
- SPARQL 쿼리 시 OWL 제약 강제하지 않음
- 추론(reasoning) 필요 시 OWL 활용 가능

### 4. 라벨 기반 검색

- 모든 인스턴스가 한글 `rdfs:label` 보유
- SPARQL에서 라벨 기반 검색 지원
- URI 직접 사용보다 라벨 검색 권장

---

## 📚 관련 파일

| 파일           | 경로                                                | 설명                         |
| -------------- | --------------------------------------------------- | ---------------------------- |
| OWL 스키마     | `ontology/korean_history.owl`                       | 온톨로지 정의                |
| TTL 인스턴스   | `ontology/instances/korean_history_instances.ttl`   | 메인 인스턴스 (205K줄)       |
| TTL 인스턴스 2 | `ontology/instances/korean_history_instances_2.ttl` | 추가 인스턴스                |
| 프로퍼티 그룹  | `ontology/instances/property_groups.json`           | 프로퍼티 분류 (203개/50그룹) |

---

## 🔧 버전 히스토리

| 버전  | 날짜    | 변경사항                                 |
| ----- | ------- | ---------------------------------------- |
| 2.0.0 | 2024-12 | TTL 기반 전면 재설계, 동적 프로퍼티 반영 |
| 1.0.0 | 2024-11 | 초기 버전                                |
