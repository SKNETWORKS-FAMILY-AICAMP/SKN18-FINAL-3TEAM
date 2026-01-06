# 🎮 minji_run 러닝 게임 완전 설정 가이드

Unity 에디터에서 **처음부터 끝까지** 설정하는 완벽 가이드

---

## 📋 목차

0. [스크립트 역할 설명](#0-스크립트-역할-설명) ⭐ NEW
1. [프로젝트 초기 설정](#1-프로젝트-초기-설정)
2. [GameConfig 생성](#2-gameconfig-생성)
3. [Scene 구조 생성](#3-scene-구조-생성)
4. [Player 설정](#4-player-설정)
5. [Camera 설정](#5-camera-설정)
6. [Managers 설정](#6-managers-설정)
7. [Track 프리팹 생성](#7-track-프리팹-생성)
8. [QuizDoor 프리팹 생성](#8-quizdoor-프리팹-생성)
9. [TrackSegment에 퀴즈 시스템 추가](#9-tracksegment에-퀴즈-시스템-추가)
10. [Obstacle 프리팹 생성](#10-obstacle-프리팹-생성)
11. [UI 구성](#11-ui-구성)
12. [참조 연결](#12-참조-연결)
13. [테스트](#13-테스트)
14. [WebGL 빌드](#14-webgl-빌드)

---

## 🎯 게임 시스템 개요

### 조작 방법
- **방향키**: 상하좌우 이동
- **Ctrl**: 점프 (더블점프 가능)
- **Z**: 대쉬 (게이지 소모, 누르고 있는 동안 대쉬)

### 게임 플로우 (하이브리드 체인 방식)
```
게임 시작 (100초 타이머 시작)
    ↓
QuizTrigger 통과 (첫 번째만)
    ↓
질문 3초 표시 (게임은 계속 진행, 플레이어 이동 가능)
    ↓
질문 숨김 + 3개 문에 정답/오답 할당
    ↓
플레이어가 문 선택
    ↓
[정답 문 통과] → +5초, 점수 +1 → 1.5초 후 다음 퀴즈 자동 시작 ⭐
[오답 문 충돌] → -5초 (한 번만), 빨간색 표시, 막힘 → 다른 문 찾기
    ↓
다음 QuizDoorController 자동 활성화 (체인) ⭐
    ↓
새 퀴즈 3개 문에 정답/오답 할당
    ↓
... (반복, 마지막 퀴즈까지)
    ↓
시간 0초 → 게임 종료
```

### 핵심 메커니즘
- **100초 타이머**: 정답 시 +5초, 오답 시 -5초
- **점수 = 정답 개수**: 정답 문 통과 시 +1
- **문 기반 퀴즈**: 정답 문은 통과 가능(Trigger), 오답 문은 벽처럼 막힘(Solid)
- **퀴즈 표시 3초**: 질문이 화면에 표시되는 동안에도 게임 계속 진행 (일시정지 없음)
- **퀴즈 중복 방지**: 한 게임에서 같은 퀴즈는 한 번만 출제 (모든 퀴즈 완료 시 더 이상 퀴즈 없음)
- **⭐ 하이브리드 체인**: 첫 QuizTrigger만 필요, 정답 시 다음 퀴즈 자동 활성화 (1.5초 후)
- **게이지 기반 대쉬**: Z 키로 대쉬, 게이지 소모 50/초, 회복 25/초
- **더블 점프**: Ctrl 키로 최대 2번 점프 가능
- **낙사 리스폰**: 떨어지면 마지막 안전 위치로 자동 복귀, 1초 스턴

---

## 0. 스크립트 역할 설명 ⭐

이 섹션에서는 프로젝트의 모든 주요 스크립트가 어떤 역할을 하는지 자세히 설명합니다.

### 📁 Core Managers (게임 핵심 관리자)

#### GameStateManager.cs
**역할:** 게임 전체 상태 관리
```
주요 기능:
- 게임 상태 전환 (Running → Quiz → Result → GameOver → GameClear)
- 게임 통계 추적 (정답 개수, 거리, 플레이 시간)
- Time.timeScale 제어 (일시정지/재개)
- 타이머 시작/정지 제어
- 플레이어 시작 위치 자동 설정
```
**핵심 메서드:**
- `ChangeState(GameState newState)`: 게임 상태 변경
- `StartQuiz()`: 퀴즈 상태로 전환 (현재는 사용 안 함, 게임 일시정지 제거)
- `CompleteQuiz(bool isCorrect, int scoreChange)`: 퀴즈 완료 처리
- `GameOver()`: 게임 종료 처리 (시간 초과)
- `GameClear()`: 게임 클리어 처리 (골 도달)
- `RestartGame()`: 게임 재시작 (InitializeGame 호출)
- `QuitGame()`: 게임 종료 (에디터: Play 모드 중지, 빌드: Application.Quit)
- `MovePlayerToStart()`: 플레이어를 StartPoint로 이동

#### GameTimerManager.cs
**역할:** 100초 제한 시간 관리
```
주요 기능:
- 100초 카운트다운 타이머
- 정답 시 +5초, 오답 시 -5초
- 타이머 종료 시 게임 오버
- HUD에 남은 시간 표시
```
**핵심 메서드:**
- `StartTimer()`: 타이머 시작 (100초)
- `AddBonusTime()`: 보너스 시간 추가 (+5초)
- `ApplyPenalty()`: 페널티 시간 감소 (-5초)
- `StopTimer()`: 타이머 정지

#### SegmentManager.cs
**역할:** 트랙 세그먼트 관리 (현재는 싱글톤만 유지)
```
현재 상태:
- 자동 생성 기능 제거됨
- 싱글톤 Instance만 제공
- 수동 맵 제작 방식으로 변경됨
```
**주의:** 이전에는 자동 세그먼트 생성 기능이 있었지만, 현재는 **Unity에서 직접 트랙을 배치하는 방식**으로 변경되었습니다.

---

### 📝 Quiz System (퀴즈 시스템)

#### QuizManager.cs
**역할:** 퀴즈 로드, 채점, 보상 관리
```
주요 기능:
- JSON 파일에서 퀴즈 데이터 로드
- 퀴즈 랜덤 선택 (중복 방지)
- 퀴즈 제한 시간 체크 (30초)
- 정답/오답 처리
```
**핵심 메서드:**
- `StartNewQuiz()`: 새 퀴즈 시작 (중복 없이)
- `SubmitAnswer(int selectedIndex)`: 답안 제출 (정답만 호출됨)
**중요:**
- `usedQuizIndices` 리스트로 출제된 퀴즈 추적
- 모든 퀴즈 완료 시 더 이상 퀴즈 나오지 않음

#### QuizDoorController.cs
**역할:** 3개 문에 정답/오답 랜덤 할당, 하이브리드 체인 지원 ⭐
```
주요 기능:
- 씬에서 QuizDoor 3개 찾기 (GetComponentsInChildren 또는 수동 할당)
- 정답 1개 + 오답 2개를 Fisher-Yates 알고리즘으로 셔플
- 각 문에 답안 텍스트 및 정답 여부 할당
- 정답 선택 시 정답 문 초록색 강조
- 정답 후 1초 뒤 문 리셋
- ⭐ 하이브리드 체인: 정답 시 다음 QuizDoorController 자동 활성화
```
**핵심 메서드:**
- `ActivateWithQuiz(QuizData quizData)`: 컨트롤러 활성화 및 퀴즈 할당
- `SpawnDoors(QuizData quizData)`: 3개 문에 퀴즈 데이터 할당 (생성이 아님!)
- `RemoveAllDoors()`: 모든 문 리셋 (파괴 안 함)
- `Deactivate()`: 컨트롤러 비활성화
- ⭐ `ActivateNextController()`: 다음 컨트롤러 자동 활성화 (체인)
**Inspector 설정:**
- **Quiz Doors** (Size: 3): QuizDoor 3개 수동 연결
- ⭐ **Next Door Controller**: 다음 QuizDoorController 연결 (체인용, 선택사항)
**주의:** "SpawnDoors"라는 이름이지만 실제로는 **기존 문에 데이터만 할당**합니다. 문을 생성하지 않습니다!

#### QuizDoor.cs
**역할:** 개별 문의 상태 관리
```
주요 기능:
- 정답/오답 상태 저장
- Collider 타입 변경 (정답: Trigger, 오답: Solid)
- 색상 변경 (정답: 초록, 오답: 빨강)
- 플레이어 충돌/통과 감지
- 오답 페널티는 한 번만 적용
```
**핵심 메서드:**
- `Initialize(int index, string choiceText, bool isCorrect)`: 문 초기화
- `OnTriggerEnter(Collider other)`: 정답 문 통과 감지
- `OnCollisionEnter(Collision collision)`: 오답 문 충돌 감지
- `ShowCorrectAnswer()`: 정답 문 초록색 표시
- `ResetDoor()`: 문 상태 초기화

#### QuizTrigger.cs
**역할:** 퀴즈 시작 트리거
```
주요 기능:
- Player가 Box Collider에 진입 시 퀴즈 시작
- 한 번만 트리거 (triggerOnce)
- 쿨다운 체크 (재사용 대기 시간)
- GameState 체크 (Running 상태일 때만)
```
**핵심 메서드:**
- `OnTriggerEnter(Collider other)`: Player 감지
- `TriggerQuiz()`: 퀴즈 시작 (GameStateManager.StartQuiz() 호출 안 함!)
**중요:** 게임 일시정지 제거를 위해 GameState를 Quiz로 변경하지 않고, QuizManager.StartNewQuiz()만 호출합니다.

---

### 🎮 Player Control (플레이어 제어)

#### RunnerController.cs
**역할:** 플레이어 이동, 점프, 대쉬 제어
```
주요 기능:
- 방향키 입력 처리 (상하좌우)
- Ctrl 더블 점프
- Z 대쉬 (게이지 기반)
- CharacterController 기반 이동
- 낙사 감지 및 리스폰 (Fall Death Y)
```
**핵심 메서드:**
- `HandleMovement()`: 이동 처리
- `HandleJump()`: 점프 처리
- `HandleDash()`: 대쉬 처리
- `CheckGrounded()`: 지면 체크
- `CheckFallDeath()`: 낙사 감지 및 리스폰
**주요 설정 (Inspector 우선):**
- `moveSpeed`: 이동 속도 (기본값: 5)
- `jumpForce`: 점프 힘 (기본값: 8) **⭐ Inspector에서 조정 가능!**
- `gravity`: 중력 (기본값: 20)
- `rotationSpeed`: 회전 속도 (기본값: 10)
- **💡 Inspector 값 우선**: Inspector에서 값을 변경하면 GameConfig보다 우선 적용됩니다
**주의:**
- `autoRun` 기능은 비활성화 (체크 해제)
- `fallDeathY` 기본값: -10 (이 높이 이하로 떨어지면 리스폰)

---

### 🎥 Camera (카메라)

#### FollowCamera.cs
**역할:** 플레이어 추적 카메라
```
주요 기능:
- 플레이어 뒤에서 부드럽게 따라가기
- Offset 기반 위치 계산
- Smooth Lerp 이동
```
**핵심 메서드:**
- `LateUpdate()`: 카메라 위치 업데이트
**설정:**
- Offset: (0, 5, -10) - 플레이어 위 5m, 뒤 10m
- Smooth Speed: 5

---

### 🎨 UI Management (UI 관리)

#### UIManager.cs
**역할:** 모든 UI 패널 표시 및 업데이트
```
주요 기능:
- HUD 패널 (점수, 거리, 타이머)
- Quiz 패널 (질문 표시)
- Result 패널 (게임 결과)
- GameOver 패널
- 대쉬 게이지 표시
```
**핵심 메서드:**
- `OnQuizLoaded(QuizData quiz)`: 퀴즈 질문 3초 표시
- `HideQuestionAndSpawnDoors()`: 질문 숨기고 문에 답안 할당
- `UpdateHUD(GameStats stats)`: HUD 업데이트
- `UpdateGameTimer(float timeRemaining)`: 타이머 업데이트
**중요:**
- 퀴즈 질문은 3초 후 자동으로 숨겨짐
- 질문이 표시되는 동안에도 게임은 계속 진행 (일시정지 없음)

---

### 🗺️ Track & Obstacles (트랙 및 장애물)

#### TrackSegment.cs
**역할:** 트랙 세그먼트 (수동 배치용)
```
주요 기능:
- 세그먼트 길이 정보 저장
- ObstacleRoot 관리 (수동 배치된 장애물 담는 부모)
- StartPoint/EndPoint 위치 제공
- 장애물 수집 (CollectObstacles)
- 장애물 제거 (ClearObstacles)
- 세그먼트 재활성화 (Recycle/Activate)
```
**핵심 메서드:**
- `Initialize(Vector3 position)`: 세그먼트 초기화
- `CollectObstacles()`: ObstacleRoot 내 장애물 수집
- `ClearObstacles()`: 모든 장애물 제거
- `Recycle()`: 비활성화
- `Activate(Vector3 position)`: 재활성화
**접근자:**
- `StartPosition`: startPoint가 있으면 그 위치, 없으면 세그먼트 중심
- `EndPosition`: endPoint가 있으면 그 위치, 없으면 세그먼트 중심 + 길이만큼 앞
**주의:**
- **자동 생성 기능 제거됨** (SpawnObstacles 메서드 삭제)
- ObstacleRoot는 Unity에서 직접 배치한 장애물을 담는 부모 역할만 수행

#### GoalTrigger.cs ⭐ (NEW)
**역할:** 골 지점 트리거 - 게임 클리어 감지
```
주요 기능:
- 플레이어가 EndPoint에 도달하면 게임 클리어
- Box Collider 자동 설정 (Is Trigger: true)
- Scene 뷰에서 초록색으로 표시
- 중복 트리거 방지
```
**핵심 메서드:**
- `OnTriggerEnter(Collider other)`: 플레이어 감지 시 GameStateManager.GameClear() 호출
**설정:**
- `triggerSize`: 트리거 크기 (기본: 5, 5, 2)
- `showGizmos`: Scene 뷰에서 표시 여부
**사용:**
- EndPoint 오브젝트에 Add Component → Goal Trigger
- 플레이어에 Tag "Player" 필요

---

### ⚙️ Data & Config (데이터 및 설정)

#### GameConfig.cs (ScriptableObject)
**역할:** 게임 전역 설정
```
주요 설정:
- Player: 이동 속도, 점프력, 중력
- Quiz: 퀴즈 제한 시간 (30초)
- Track: 세그먼트 길이, 폭
- Camera: 오프셋, 부드러운 이동 속도
- Performance: 프레임레이트, 그림자 on/off
```
**사용 방법:** Assets에서 우클릭 → Create → minji_run → Game Config

#### QuizData.cs
**역할:** 퀴즈 데이터 구조
```csharp
public class QuizData
{
    public string question;          // 질문
    public string correctAnswer;     // 정답 (1개)
    public string[] wrongAnswers;    // 오답 (2개)
    public string explanation;       // 해설
    public int rewardScore;          // 보상 점수
}
```

#### GameStats.cs
**역할:** 게임 통계 데이터
```csharp
public class GameStats
{
    public int correctAnswers;   // 정답 개수 (점수)
    public int wrongAnswers;     // 오답 개수
    public float runDistance;    // 달린 거리
    public float playTime;       // 플레이 시간
    public int totalScore;       // 총 점수
}
```

#### GameState.cs (Enum)
**역할:** 게임 상태 정의
```csharp
public enum GameState
{
    Running,   // 게임 진행 중
    Quiz,      // 퀴즈 중 (현재 미사용)
    Result,    // 결과 표시
    GameOver   // 게임 종료
}
```

---

### 🔧 Utility Scripts (유틸리티)

#### QuizPanelDiagnostic.cs
**역할:** Quiz Panel UI 디버깅 도구
```
주요 기능:
- Quiz Panel 활성화 상태 체크
- QuestionText 컴포넌트 체크
- Alpha 값 자동 수정 (0이면 흰색으로 변경)
- 폰트 사이즈 자동 수정 (너무 작으면 48로 변경)
- 테스트 텍스트 설정
```
**사용 방법:** Quiz Panel에 붙이고 Play 모드에서 Space 키 누르기
**주의:** 개발/디버깅 전용 스크립트입니다. 릴리즈 시 제거 가능.

---

## 📊 스크립트 간 관계도

```
GameStateManager (게임 상태)
    ↓ 제어
GameTimerManager (타이머)
    ↓ 시간 종료
GameStateManager.GameOver()

QuizTrigger (트리거)
    ↓ 퀴즈 시작
QuizManager (퀴즈 관리)
    ↓ 문에 할당
QuizDoorController (문 관리)
    ↓ 초기화
QuizDoor × 3 (개별 문)
    ↓ 정답 선택
QuizManager.SubmitAnswer()
    ↓ 보너스
GameTimerManager.AddBonusTime()

RunnerController (플레이어)
    ↓ 위치
FollowCamera (카메라 추적)

All Managers
    ↓ UI 이벤트
UIManager (UI 표시)
```

---

### 🏗️ Unity Hierarchy 오브젝트 역할 설명

Unity Hierarchy에 배치되는 각 오브젝트의 역할을 설명합니다.

#### 📦 Core Objects (핵심 오브젝트)

##### Managers (빈 오브젝트)
**역할:** 모든 매니저 스크립트를 담는 컨테이너
```
구조:
Managers
├─ GameStateManager (컴포넌트)
├─ GameTimerManager (컴포넌트)
├─ QuizManager (컴포넌트)
├─ QuizDoorController (컴포넌트)
└─ SegmentManager (컴포넌트)
```
**주의:**
- Transform 위치: `(0, 0, 0)`
- 모든 싱글톤 매니저를 하나의 오브젝트에 모아 관리
- 씬 시작 시 자동으로 초기화됨

##### Player (빈 오브젝트)
**역할:** 플레이어 캐릭터 (실제 게임 조작 대상)
```
필수 컴포넌트:
- CharacterController (Unity 내장)
- Rigidbody (Is Kinematic = true, Use Gravity = false)
- RunnerController (스크립트)
```
**설정:**
- Tag: `Player` ⭐ 필수!
- Position: `(0, 1, 0)`
- Rigidbody가 없으면 퀴즈 트리거가 작동하지 않음!

##### Main Camera
**역할:** 플레이어를 따라다니는 카메라
```
필수 컴포넌트:
- Camera (Unity 기본)
- FollowCamera (스크립트)
```
**설정:**
- Tag: `MainCamera`
- Position: `(0, 5, -10)` (초기 위치)
- FollowCamera 스크립트에서 Player Transform 연결 필요

##### Directional Light
**역할:** 씬 전체 조명
```
설정:
- Rotation: (50, -30, 0) (권장)
- Intensity: 1
- Shadow Type: No Shadows (WebGL 최적화)
```

##### Canvas
**역할:** 모든 UI 요소의 부모
```
구조:
Canvas (UIManager 컴포넌트 여기 부착!)
├─ HUD Panel (게임 중 상시 표시 UI)
│   ├─ Score Text (점수)
│   ├─ Timer Text (남은 시간)
│   └─ Dash Gauge Image (대쉬 게이지)
├─ Quiz Panel (퀴즈 질문 표시)
│   └─ Question Text
├─ Result Panel (퀴즈 정답/오답 결과)
│   └─ Result Text
└─ GameOver Panel (게임 종료 화면)
    ├─ Title Text
    ├─ Final Score Text
    └─ Restart Button
```
**설정:**
- Render Mode: Screen Space - Overlay
- Canvas Scaler: Scale With Screen Size
- UIManager 스크립트가 여기 부착됨 (Managers가 아님!)

##### EventSystem
**역할:** UI 입력 이벤트 처리 (버튼 클릭 등)
```
주의:
- Canvas 생성 시 자동으로 생성됨
- Canvas의 자식이 아닌 형제 (같은 레벨)
- 삭제하면 UI 버튼이 작동하지 않음!
```

##### Track (빈 오브젝트)
**역할:** 수동으로 배치한 트랙 세그먼트들의 부모
```
구조 예시:
Track
├─ TrackSegment_01 (프리팹)
├─ TrackSegment_02 (프리팹)
└─ TrackSegment_03 (프리팹)
```
**주의:**
- 자동 생성 기능이 제거되어 Unity에서 직접 배치해야 함
- 각 TrackSegment에 TrackSegment.cs 스크립트 부착

---

#### 🎯 Quiz System Objects (퀴즈 시스템 오브젝트)

##### QuizTrigger (Cube)
**역할:** 플레이어가 통과하면 퀴즈 시작
```
필수 컴포넌트:
- Box Collider (Is Trigger = true)
- QuizTrigger (스크립트)
- Mesh Renderer (시각 효과, 선택사항)
```
**설정:**
- Tag: 없음 (Player 태그 감지)
- Position: 트랙 중간에 배치 (예: (0, 2, 25))
- Box Collider Size: (4, 5, 2) (스크립트에서 자동 설정)
- 색상: 노란색 (triggerColor)
**동작:**
- Player가 진입하면 QuizManager.StartNewQuiz() 호출
- 게임은 계속 진행 (일시정지 없음)
- 한 번 트리거되면 자동 비활성화

##### QuizDoor (Cube x3)
**역할:** 퀴즈 답안을 표시하는 3개 문 (정답 1개 + 오답 2개)
```
필수 컴포넌트:
- QuizDoor (스크립트)
- Box Collider (Is Trigger = false for wrong, true for correct)
- Mesh Renderer + Material (색상 표시용)
- TextMeshPro - Text (3D) (답안 텍스트)
```
**설정:**
- Tag: 없음
- Position: 트랙 위에 3개 나란히 배치
  - 왼쪽 문: (-3, 1.5, 30)
  - 가운데 문: (0, 1.5, 30)
  - 오른쪽 문: (3, 1.5, 30)
- Scale: (2, 3, 0.5) (폭 2m, 높이 3m, 두께 0.5m)
**동작:**
- QuizDoorController가 정답/오답을 랜덤 할당
- 정답 문: Trigger 모드 (통과 가능, 초록색)
- 오답 문: Solid 모드 (막힘, 빨간색)
- 정답 선택 시 1초 후 자동 리셋

---

#### 🏃 Track & Obstacles (트랙 및 장애물)

##### TrackSegment (Prefab)
**역할:** 재사용 가능한 트랙 조각
```
구조:
TrackSegment_01
├─ Ground (Cube) - 실제 바닥
├─ StartPoint (빈 오브젝트)
├─ EndPoint (빈 오브젝트)
├─ ObstacleRoot (빈 오브젝트)
│   ├─ Obstacle_Box (배치된 장애물)
│   └─ Obstacle_Sphere (배치된 장애물)
└─ QuizTrigger (퀴즈 트리거, 선택사항)
```
**필수 컴포넌트:**
- TrackSegment (스크립트)
**설정:**
- Ground Tag: `Ground`
- Ground Scale: (10, 0.2, 50) (폭 10m, 길이 50m)
- StartPoint Position: (0, 0, 0) (로컬)
- EndPoint Position: (0, 0, 50) (로컬)
- ObstacleRoot: 장애물들의 부모

##### ObstacleRoot (빈 오브젝트)
**역할:** 트랙 세그먼트 내 모든 장애물의 부모
```
주의:
- TrackSegment의 자식으로 배치
- CollectObstacles() 메서드가 여기서 장애물 수집
- 자동 생성 기능은 제거됨 (수동 배치만)
```

##### Obstacle (Prefab)
**역할:** 플레이어가 피해야 하는 장애물
```
종류:
- Obstacle_Box (큐브 형태)
- Obstacle_Sphere (구 형태)
- Obstacle_Cylinder (원기둥 형태)
```
**필수 컴포넌트:**
- Collider (Box/Sphere/Capsule)
- Rigidbody (Is Kinematic = true) (선택사항)
**설정:**
- Tag: `Obstacle`
- Position: ObstacleRoot 내에 배치
- Scale: (1, 1, 1) ~ (2, 2, 2)

---

#### ⚙️ Optional Objects (선택 오브젝트)

---

### 📊 Hierarchy 전체 구조 예시 (하이브리드 체인 방식) ⭐

```
Hierarchy:
├─ Directional Light
├─ Main Camera (FollowCamera)
├─ Managers (빈 오브젝트)
│   ├─ GameStateManager
│   ├─ GameTimerManager
│   ├─ QuizManager
│   └─ SegmentManager
├─ Player (CharacterController + Rigidbody + RunnerController)
├─ Track (빈 오브젝트)
│   │
│   ├─ QuizZone_1 (첫 번째 퀴즈 - QuizTrigger 필요)
│   │   ├─ QuizTrigger (Box Collider, Is Trigger)
│   │   │   └─ DoorController_1 (QuizDoorController.cs) ⭐
│   │   └─ Doors_1
│   │       ├─ QuizDoor_1 (문 3D 모델 + QuizDoor.cs)
│   │       ├─ QuizDoor_2
│   │       └─ QuizDoor_3
│   │
│   ├─ QuizZone_2 (두 번째 퀴즈 - QuizTrigger 없음!) ⭐
│   │   ├─ DoorController_2 (QuizDoorController.cs) ⭐
│   │   └─ Doors_2
│   │       ├─ QuizDoor_1
│   │       ├─ QuizDoor_2
│   │       └─ QuizDoor_3
│   │
│   ├─ QuizZone_3 (마지막 퀴즈 - QuizTrigger 없음!)
│   │   ├─ DoorController_3 (QuizDoorController.cs)
│   │   └─ Doors_3
│   │       ├─ QuizDoor_1
│   │       ├─ QuizDoor_2
│   │       └─ QuizDoor_3
│   │
│   ├─ TrackSegment_01 (일반 트랙)
│   │   ├─ Ground (Cube)
│   │   ├─ StartPoint
│   │   ├─ EndPoint
│   │   └─ ObstacleRoot
│   │       ├─ Obstacle_Box (Tag: Obstacle)
│   │       └─ Obstacle_Sphere (Tag: Obstacle)
│   ├─ TrackSegment_02
│   └─ TrackSegment_03
│
├─ Canvas (UIManager)
│   ├─ HUD Panel (활성화)
│   ├─ Quiz Panel (비활성화)
│   ├─ Result Panel (비활성화)
│   └─ GameOver Panel (비활성화)
└─ EventSystem
```

**⭐ 하이브리드 체인 핵심 구조:**
- **QuizZone_1**: QuizTrigger + DoorController_1 (자식)
- **QuizZone_2, 3**: DoorController만 (QuizTrigger 없음)
- **Next Door Controller 체인**: 1 → 2 → 3 → None

---

## 1. 프로젝트 초기 설정

### 1.1 필수 패키지 설치
1. **Window → Package Manager**
2. 다음 패키지 설치:
   - **TextMeshPro** (Unity Registry)
   - **Input System** (선택사항, 기본 Input Manager 사용)

### 1.2 Tags 설정
**Edit → Project Settings → Tags and Layers**

Tags 추가:
- `Player` (필수)
- `Obstacle` (필수)

**주의:** `Ground` Tag는 **불필요**합니다 (설정하지 마세요)

### 1.3 Layers 설정 (선택사항, 권장)
User Layer 8: `Ground` (지면 체크용, 더블점프 안정성)

**⚠️ Ground Layer:**
- 설정하지 않아도 기본 동작하지만, 안정적인 더블점프를 위해 권장
- RunnerController가 바닥 감지 시 사용
- TrackSegment의 Ground 오브젝트에도 동일한 Layer 적용 필요 (Section 7.2)

### 1.4 Physics 설정
**Edit → Project Settings → Physics**
- Gravity Y: `-20` (기본값보다 강하게)

---

## 2. GameConfig 생성

### 2.1 ScriptableObject 생성
1. **Project 창** → `Assets/` 폴더 우클릭
2. **Create → minji_run → Game Config**
3. 이름: `GameConfig`

### 2.2 GameConfig 설정
Inspector에서 다음과 같이 설정:

```
Player Settings:
- Move Speed: 5
- Jump Force: 8
- Gravity: 20
- Rotation Speed: 10

Quiz Settings:
- Quiz Time Limit: 30
- Quiz Interval: 50 (현재 코드에서 미사용, 트리거 배치 방식)

Track Settings:
- Segment Length: 50
- Segment Width: 10

Camera Settings:
- Camera Offset: (0, 5, -10)
- Camera Smooth Speed: 5

Performance (WebGL):
- Object Pool Size: 20
- Enable Shadows: false (체크 해제)
- Target Frame Rate: 60
```

---

## 3. Scene 구조 생성

### 3.1 기본 Scene 구조
**Hierarchy**에서 다음과 같이 구성:

```
Hierarchy:
├─ Directional Light (기존)
├─ Main Camera (기존)
├─ Managers (빈 오브젝트) ⭐ QuizDoorController 없음!
├─ Player (빈 오브젝트)
├─ Track (빈 오브젝트)
├─ Canvas (UI → Canvas로 생성)
└─ EventSystem (자동 생성)
```

**⚠️ 중요: Managers에는 QuizDoorController가 없습니다!**
- QuizDoorController는 각 QuizZone의 DoorController로 배치

**⚠️ 참고:**
- **EventSystem**은 Canvas의 **자식이 아닌 형제**(같은 레벨)입니다
- Unity에서 Canvas를 생성하면 EventSystem이 자동으로 Hierarchy 루트에 생성됩니다

### 3.2 위치 설정
- **Managers**: `(0, 0, 0)`
- **Player**: `(0, 1, 0)`
- **Track**: `(0, 0, 0)`
- **Main Camera**: `(0, 5, -10)`

### 3.3 낙사 감지 설정 ⭐

**✅ 자동 낙사 감지 (추천)**

RunnerController가 **Y 위치 기반**으로 자동 낙사 감지를 합니다.

**Player 선택 → RunnerController 컴포넌트:**
- **Fall Death Y**: `-10` (이 높이 이하로 떨어지면 자동 리스폰)

**동작 방식:**
- 플레이어 Y 위치 < -10 → 자동 리스폰
- 마지막 안전 위치(지면에 있던 곳)로 복귀
- 리스폰 후 1초간 조작 불가 (스턴)
---

## 4. Player 설정

### 4.1 Player 기본 설정
1. **Player** 오브젝트 선택
2. Inspector:
   - **Tag**: `Player`
   - **Position**: `(0, 1, 0)`

### 4.2 Rigidbody 추가 (필수!) ⭐⭐⭐

**⚠️ 매우 중요: Rigidbody는 반드시 필요합니다!**

Unity에서 **Trigger 충돌 감지**가 작동하려면 충돌하는 두 오브젝트 중 **최소 하나**는 Rigidbody를 가져야 합니다.

**왜 필요한가?**
- QuizTrigger가 Player를 감지하려면 Player에 Rigidbody 필요
- Rigidbody가 없으면 OnTriggerEnter가 **즉시 호출되지 않거나 아예 호출되지 않음**
- 퀴즈 시스템이 작동하지 않는 가장 큰 원인!

---

#### 4.2.1 Rigidbody 추가

1. **Player 오브젝트 선택**
2. **Inspector → Add Component → Rigidbody**

---

#### 4.2.2 Rigidbody 설정 ⚠️

**중요: CharacterController와 함께 사용하려면 다음 설정 필수!**

**Mass (질량):**
- `1` (기본값)

**Drag (공기 저항):**
- `0` (기본값)

**Angular Drag (회전 저항):**
- `0.05` (기본값)

**Use Gravity:**
- ❌ **체크 해제** (CharacterController가 중력을 처리하므로 불필요)
- ⚠️ 체크하면 플레이어가 이중으로 떨어짐!

**Is Kinematic:** ⭐⭐⭐
- ✅ **체크** (매우 중요!)
- **Kinematic이란?** 물리 엔진이 아닌 스크립트가 직접 움직임을 제어
- CharacterController가 이미 움직임을 처리하므로 Kinematic 모드 사용
- Is Kinematic = false이면 물리 충돌에 영향받아 플레이어가 밀림

**Interpolate:**
- `None` (기본값)

**Collision Detection:**
- `Discrete` (기본값)

**Constraints (제약):** ⭐
- **Freeze Position**: 모두 체크 해제
- **Freeze Rotation**:
  - **X**: ✅ 체크 (플레이어가 앞뒤로 넘어지지 않음)
  - **Y**: ❌ 체크 해제 (좌우 회전 가능하게)
  - **Z**: ✅ 체크 (플레이어가 옆으로 넘어지지 않음)

---

#### 4.2.3 최종 Rigidbody 설정 요약

```
Rigidbody:
├─ Mass: 1
├─ Drag: 0
├─ Angular Drag: 0.05
├─ Use Gravity: ❌ 체크 해제
├─ Is Kinematic: ✅ 체크 (필수!)
├─ Interpolate: None
├─ Collision Detection: Discrete
└─ Constraints:
   ├─ Freeze Position: X ❌, Y ❌, Z ❌
   └─ Freeze Rotation: X ✅, Y ❌, Z ✅
```

**⚠️ 가장 중요한 설정:**
1. **Is Kinematic: 체크 ✅** (CharacterController와 충돌 방지)
2. **Use Gravity: 체크 해제 ❌** (이중 중력 방지)
3. **Freeze Rotation X, Z: 체크 ✅** (플레이어가 넘어지지 않음)

---

#### 4.2.4 Rigidbody가 없을 때 발생하는 문제

❌ **증상:**
- QuizTrigger를 통과해도 퀴즈가 시작되지 않음
- 퀴즈가 시작되지만 **몇 초 지연** 후에 시작됨
- Console에 "[QuizTrigger] OnTriggerEnter called!" 로그가 안 나옴

❌ **원인:**
- Unity의 물리 엔진은 Rigidbody가 있는 오브젝트만 매 프레임 추적
- Rigidbody가 없으면 OnTriggerEnter가 즉시 호출되지 않음

✅ **해결:**
- Player에 Rigidbody 추가 (Is Kinematic = true)

---

### 4.3 CharacterController 추가
**Add Component → Character Controller**

설정:
- Center: `(0, 1, 0)`
- Radius: `0.5`
- Height: `2`
- Slope Limit: `45`
- Step Offset: `0.3`

**⚠️ 참고:**
- CharacterController와 Rigidbody(Is Kinematic)를 함께 사용하면 안정적인 캐릭터 이동 가능
- CharacterController가 움직임 처리, Rigidbody가 Trigger 감지 처리

---

### 4.4 RunnerController 추가
**Add Component → Runner Controller**

**Movement 설정:**
- Move Speed: `5`
- Jump Force: `8`
- Gravity: `20`
- Rotation Speed: `10`
- Max Jump Count: `2` (더블점프)

**💡 Inspector 값 우선 설정 ⭐ NEW**
- Inspector에서 설정한 값은 **GameConfig보다 우선 적용**됩니다
- 예: Jump Force를 Inspector에서 `12`로 변경 → `12`가 적용됨 (GameConfig 무시)
- 기본값(`5`, `8`, `20`, `10`)을 그대로 두면 GameConfig 값 사용
- **점프 높이 조정이 필요할 때**: Inspector의 Jump Force만 변경하면 됨!

**Dash 설정:**
- Dash Speed: `15`
- Max Dash Gauge: `100`
- Dash Gauge Depletion Rate: `20` (초당 소모)
- Dash Gauge Recovery Rate: `10` (초당 회복)

**Ground Check:**
- Ground Check Distance: `0.2`
- Ground Layer: `Ground` (권장) 또는 `Everything`
  - ⚠️ TrackSegment의 Ground 오브젝트 Layer와 일치해야 함 (Section 7.2 참고)
  - 설정하지 않아도 작동하지만, 안정적인 더블점프를 위해 권장
- **Fall Death Y**: `-10` (⭐ 이 높이 이하로 떨어지면 자동 리스폰)

**Auto Run:**
- Auto Run: **체크 해제** (자동 전진 비활성화)

---

### 4.5 Player 시각화 (임시)
1. **Player 우클릭 → 3D Object → Capsule**
2. 이름: `Model`
3. 설정:
   - Position: `(0, 0, 0)` (로컬)
   - **Capsule Collider 제거** (Remove Component)

---

### 4.6 Player 설정 최종 확인 ✅

Player 오브젝트에 다음 컴포넌트들이 모두 있어야 합니다:

**필수 컴포넌트 체크리스트:**
- [ ] **Transform** (기본)
- [ ] **Rigidbody** (Is Kinematic = true, Use Gravity = false) ⭐
- [ ] **Character Controller**
- [ ] **Runner Controller**
- [ ] **Tag**: `Player`

**⚠️ 가장 흔한 실수:**
- Rigidbody가 없음 → 퀴즈 트리거가 작동하지 않음!
- Is Kinematic 체크 안함 → 플레이어가 물리 충돌에 밀림
- Use Gravity 체크함 → 플레이어가 이중으로 떨어짐

---

## 5. Camera 설정

### 5.1 FollowCamera 추가
**Main Camera 선택 → Add Component → Follow Camera**

설정:
- **Target**: `Player` Transform 드래그
- **Offset**: `(0, 5, -10)`
- **Smooth Speed**: `5`
- **Look At Target**: 체크
- **Allow Rotation**: 체크 해제
- **Allow Zoom**: 체크 해제

---

## 6. Managers 설정

### 6.1 Managers 구조 생성
**Managers 우클릭 → Create Empty**로 다음 생성:

```
Managers/
├─ GameStateManager
├─ GameTimerManager
├─ QuizManager
└─ SegmentManager
```

**⚠️ 중요: QuizDoorController는 Managers에 없습니다!**
- QuizDoorController는 **각 QuizTrigger의 자식**으로 만듭니다
- 섹션 9.4에서 설명 (TrackSegment에 퀴즈 시스템 추가)

---

### 6.2 GameStateManager 설정

**Managers/GameStateManager 선택 → Add Component → Game State Manager**

설정:
- **Game Config**: `GameConfig` 드래그
- **Player**: `Player` 오브젝트 드래그 ⭐
- **Start Track Segment**: 시작 트랙 세그먼트 드래그 (Section 7에서 생성) ⭐
- **Current State**: `Running`

**⚠️ 새로운 기능:**
- **Player 시작 위치 자동 설정**: 게임 시작/재시작 시 플레이어를 StartTrackSegment의 StartPoint로 자동 이동
- **게임 클리어**: 플레이어가 EndPoint에 도달하면 게임 클리어 (Section 7.8 참고)

---

### 6.3 GameTimerManager 설정 ⭐

**Managers/GameTimerManager 선택 → Add Component → Game Timer Manager**

설정:
- **Start Time**: `100` (100초 제한 시간)
- **Bonus Time**: `5` (정답 시 +5초)
- **Penalty Time**: `5` (오답 시 -5초)

**역할:**
- 게임 시작 시 100초 타이머 시작
- 정답 문 통과 시 +5초 추가
- 오답 문 충돌 시 -5초 감소 (문당 한 번만)
- 시간 0초 되면 게임 오버

---

### 6.4 QuizManager 설정

**Managers/QuizManager 선택 → Add Component → Quiz Manager**

설정:
- **Quiz Json File**: 비워둠 (Resources에서 자동 로드)
- **Shuffle Quizzes**: 체크
- **Shuffle Choices**: 체크

**역할:**
- 퀴즈 데이터 로드 및 관리
- 정답 체크 및 정답 개수(점수) 누적
- 정답 시 GameTimerManager.AddBonusTime() 호출

---

### 6.5 UIManager 설정

UIManager는 **Canvas**에 붙입니다. (10~11장 참고)

참조는 나중에 UI 생성 후 연결

---

### 6.6 SegmentManager 설정

**Managers/SegmentManager 선택 → Add Component → Segment Manager**

**주의:** SegmentManager는 현재 싱글톤 Instance만 제공합니다.
- 자동 세그먼트/장애물 생성 기능이 제거되었습니다.
- Unity에서 수동으로 트랙을 배치하는 방식으로 변경되었습니다.
- 별도의 설정이 필요 없습니다.

---

## 7. Track 프리팹 생성 ⭐

**⚠️ 중요:** 트랙 프리팹은 **루트 Scale을 (1, 1, 1)로 유지**해야 자식 오브젝트(문, 장애물 등)가 정상 크기로 보입니다!

### 7.1 TrackSegment 루트 오브젝트 생성
1. **Hierarchy 우클릭 → Create Empty**
2. 이름: `TrackSegment_01`
3. Transform 설정:
   - **Position**: `(0, 0, 0)`
   - **Scale**: `(1, 1, 1)` ⭐ **반드시 1, 1, 1로 유지!**

### 7.2 Ground (바닥) 추가
1. **TrackSegment_01 우클릭 → 3D Object → Cube**
2. 이름: `Ground`
3. Transform 설정 (로컬):
   - Position: `(0, 0, 0)`
   - Scale: `(50, 0.2, 50)` (폭 50m, 높이 0.2m, 길이 50m)
4. **Layer 설정** (권장): `Ground`
   - Inspector 상단의 Layer 드롭다운 → "Ground" 선택
   - Ground Layer가 없으면 먼저 생성 (Edit → Project Settings → Tags and Layers)

**⚠️ Layer 설정 (선택사항):**
- RunnerController가 더 안정적인 바닥 감지를 위해 Ground Layer를 사용합니다
- 설정하지 않아도 대부분 작동하지만, 점프가 불안정할 수 있습니다
- **권장**: 안정적인 더블점프를 원하면 설정하세요
- Tag는 설정하지 않아도 됩니다 (Untagged 그대로)

**설명:**
- 루트는 Scale (1,1,1)로 유지
- **Ground Cube만** 큰 스케일 적용
- 이렇게 해야 나중에 추가할 문, 장애물이 찌그러지지 않음!

### 7.3 ObstacleRoot 추가
1. **TrackSegment_01 우클릭 → Create Empty**
2. 이름: `ObstacleRoot`
3. Position: `(0, 0, 0)` (로컬)

### 7.4 TrackSegment 스크립트 추가
**TrackSegment_01 선택 → Add Component → Track Segment**

Inspector 설정:
- **Segment Length**: `50`
- **Obstacle Root**: `ObstacleRoot` 드래그

### 7.5 Material 생성 (선택사항)
1. **Project → Assets 우클릭 → Create → Material**
2. 이름: `TrackMaterial`
3. 색상: 회색
4. **Ground의 Mesh Renderer**에 적용 (루트가 아님!)

### 7.6 Prefab 저장
1. **Project 창에서 `Assets/Prefabs/` 폴더 생성** (없으면)
2. **TrackSegment_01을 Prefabs 폴더로 드래그**
3. 프리팹 생성 확인 후 **Hierarchy에서 TrackSegment_01 삭제**

**최종 프리팹 구조:**
```
TrackSegment_01 (Empty, Scale: 1, 1, 1) ⭐
├─ Ground (Cube, Scale: 50, 0.2, 50, Layer: Ground)
└─ ObstacleRoot (빈 오브젝트)
```

**⚠️ 중요:**
- TrackSegment 루트는 Empty GameObject, Scale (1,1,1) 유지
- Ground만 Scale (50, 0.2, 50) 적용
- Ground Layer 설정 권장 (점프 안정성)

---

### 7.7 StartPoint 추가 (게임 시작 위치) ⭐

게임 시작 시 플레이어가 자동으로 이동할 위치를 설정합니다.

1. **첫 번째 TrackSegment 프리팹을 Hierarchy에 배치**
   - 이름: `StartTrackSegment`

2. **StartPoint 생성**:
   - StartTrackSegment 우클릭 → Create Empty
   - 이름: `StartPoint`
   - Position: 플레이어가 시작할 위치로 이동
     - 예: `(0, 1, -20)` (트랙 시작 부분, 지면 위 1m)

3. **TrackSegment 스크립트에 연결**:
   - StartTrackSegment 선택
   - Track Segment 컴포넌트에서
   - **Start Point**: 방금 만든 StartPoint 드래그

4. **GameStateManager에 연결** (Section 6.2):
   - Managers/GameStateManager 선택
   - **Start Track Segment**: StartTrackSegment 드래그

**작동 방식:**
- 게임 시작 시: 플레이어가 자동으로 StartPoint 위치로 이동
- 게임 재시작 시: 플레이어가 다시 StartPoint로 복귀
- StartPoint를 설정하지 않으면 TrackSegment 중심이 시작점

**구조:**
```
StartTrackSegment (Empty, Scale: 1, 1, 1)
├─ Ground (Cube, Scale: 50, 0.2, 50)
├─ ObstacleRoot
└─ StartPoint (Empty) ← 플레이어 시작 위치
```

---

### 7.8 EndPoint + GoalTrigger 추가 (게임 클리어) ⭐

플레이어가 EndPoint에 도달하면 게임이 클리어됩니다.

1. **마지막 TrackSegment 생성**:
   - Hierarchy에 마지막 트랙 세그먼트 배치
   - 이름: `EndTrackSegment`

2. **EndPoint 생성**:
   - EndTrackSegment 우클릭 → Create Empty
   - 이름: `EndPoint`
   - Position: 골 지점 위치로 이동
     - 예: `(0, 0, 0)` (트랙 끝부분)

3. **GoalTrigger 추가**:
   - EndPoint 선택
   - Add Component → **Goal Trigger**
   - 설정:
     - **Trigger Size**: `(5, 5, 2)` (조절 가능)
     - **Show Gizmos**: ✅ 체크 (Scene에서 초록색으로 표시)

4. **TrackSegment 스크립트에 연결** (선택사항):
   - EndTrackSegment 선택
   - Track Segment 컴포넌트에서
   - **End Point**: EndPoint 드래그

**작동 방식:**
- 플레이어가 EndPoint 트리거에 진입 → 게임 클리어!
- GameState가 GameClear로 변경
- 타이머 정지, 게임 일시정지
- Console에 클리어 메시지 + 최종 점수/거리/시간 표시

**Scene 뷰에서:**
- StartPoint: (기본 흰색)
- EndPoint (GoalTrigger): 초록색 박스로 표시

**구조:**
```
EndTrackSegment (Empty, Scale: 1, 1, 1)
├─ Ground (Cube, Scale: 50, 0.2, 50)
├─ ObstacleRoot
└─ EndPoint (Empty + GoalTrigger + Box Collider)
    └─ 초록색 골 지점 트리거
```

**⚠️ 주의:**
- Player에 Tag "Player"가 설정되어 있어야 GoalTrigger가 감지합니다
- GoalTrigger는 자동으로 Box Collider를 추가합니다 (Is Trigger: ✅)

---

## 8. QuizDoor 프리팹 생성 ⭐ (간단 버전)

퀴즈 문은 플레이어가 답을 선택하기 위해 통과하는 오브젝트입니다.

**⚠️ 중요:** 문은 **Cube 하나**로 간단하게 만듭니다!

### 8.1 QuizDoor 생성 (Cube)
1. **Hierarchy 우클릭 → 3D Object → Cube**
2. 이름: `QuizDoor`
3. Transform 설정:
   - **Position**: `(0, 1.5, 10)`
   - **Rotation**: `(0, 0, 0)`
   - **Scale**: `(3, 3, 0.3)` (폭 3m, 높이 3m, 두께 0.3m)

### 8.2 Box Collider 설정
**QuizDoor에 자동으로 있음 (Cube 생성 시)**

Inspector 확인:
- **Is Trigger**: ✅ 체크 (기본값, QuizDoor 스크립트가 정답/오답에 따라 자동 조정)
- **Center**: `(0, 0, 0)` (기본값)
- **Size**: `(1, 1, 1)` (기본값)

**역할:**
- 플레이어가 문을 통과하면 답안 선택
- 정답 문: QuizDoor.cs가 자동으로 Trigger 유지 (통과 가능)
- 오답 문: QuizDoor.cs가 자동으로 Solid로 변경 (막힘)

---

### 8.3 QuizDoor 스크립트 추가
**QuizDoor 선택 → Add Component → Quiz Door**

Inspector 설정 (모두 기본값으로 두세요, 런타임에 자동 설정됨):
- **Choice Index**: `0`
- **Choice Text**: 비워둠
- **Is Correct Answer**: 체크 해제
- **Choice Label**: 다음 단계에서 연결
- **Normal Color**: 흰색 `(255, 255, 255)`
- **Correct Color**: 초록색 `(0, 255, 0)`
- **Wrong Color**: 빨간색 `(255, 0, 0)`

---

### 8.4 TextMeshPro 텍스트 추가
**QuizDoor 우클릭 → 3D Object → Text - TextMeshPro**

**⚠️ 처음 TextMeshPro 사용 시:**
- "Import TMP Essentials" 창이 뜨면 **Import TMP Essentials** 버튼 클릭
- 임포트 완료 후 다시 TextMeshPro 생성

**TextMeshPro 설정:**
1. 이름: `AnswerText`
2. Transform (로컬):
   - **Position**: `(0, 0, 0.2)` (문 앞쪽)
   - **Rotation**: `(0, 0, 0)`
   - **Scale**: `(1, 1, 1)`

3. **TextMeshPro 컴포넌트:**
   - **Text**: `"답안"` (임시, 런타임에 변경됨)
   - **Font Size**: `1.5`
   - **Alignment**: Center (가로/세로 중앙)
   - **Color**: 검은색 `(0, 0, 0)` (흰색 문에 검은 글씨)
   - **Font Style**: Bold
   - **Wrapping**: Enabled
   - **Overflow**: Overflow (텍스트가 잘리지 않게)

4. **Rect Transform:**
   - **Width**: `2.5`
   - **Height**: `2.5`

---

### 8.5 QuizDoor 스크립트에 텍스트 연결
**QuizDoor 루트 오브젝트 선택**

Inspector에서:
- **Choice Label**: `AnswerText` TextMeshPro 드래그

---

### 8.6 Material 추가 (선택사항)
문 색상을 변경하려면:
1. **Project → Create → Material**
2. 이름: `DoorMaterial`
3. Color: 흰색 또는 원하는 색상
4. **QuizDoor의 Mesh Renderer**에 드래그

---

### 8.7 Prefab 저장
1. **Project 창에서 `Assets/Prefabs/` 폴더로 이동** (없으면 생성)
2. **QuizDoor를 Prefabs 폴더로 드래그**
3. 프리팹 생성 확인 후 **Hierarchy에서 QuizDoor 삭제**

**최종 프리팹 구조:**
```
QuizDoor (Cube, Scale: 3, 3, 0.3)
└─ AnswerText (TextMeshPro 3D)
```

---

## 9. TrackSegment에 퀴즈 시스템 추가 ⭐ (업데이트: 2025-12-30)

이제 **StartTrackSegment**와 **DoorTrackSegment**를 사용하여 **각 퀴즈 위치마다 독립적인 퀴즈 시스템**을 만듭니다.

**⚠️ 중요한 구조 특징:**
- **StartTrackSegment**: QuizTrigger + QuizDoorController (퀴즈 시작 지점)
- **DoorTrackSegment**: 실제 QuizDoor 3개 (별도 위치)
- **수동 연결**: Unity Inspector에서 QuizDoorController의 Quiz Doors 배열에 문 3개를 수동으로 할당
- **장점**: 트리거 위치와 문 위치를 완전히 분리 가능

**⚠️ 전제 조건:**
- Section 7에서 만든 TrackSegment 구조 (Empty 루트 + Ground 자식)를 사용합니다
- Section 8에서 만든 QuizDoor 프리팹이 준비되어 있어야 합니다

---

### 9.1 StartTrackSegment 프리팹 준비

**목적**: 퀴즈 트리거를 포함하는 TrackSegment 생성

1. **Project 창**에서 **TrackSegment_01** 프리팹 복제
2. 이름 변경: `StartTrackSegment`
3. 프리팹 더블클릭하여 편집 모드 진입

**구조 (시작):**
```
StartTrackSegment (Empty, Scale: 1, 1, 1)
├── Ground (Cube, Scale: 50, 0.2, 50)
└── ObstacleRoot (기존)
```

---

### 9.2 QuizTrigger 오브젝트 생성

**StartTrackSegment 프리팹 안에:**

1. **StartTrackSegment 루트 우클릭 → Create Empty**
2. 이름: `QuizTrigger`
3. **Position**: `(0, 0, -10)` (트랙 앞쪽)

**구조:**
```
StartTrackSegment (Empty, Scale: 1, 1, 1)
├── Ground (Cube, Scale: 50, 0.2, 50)
├── ObstacleRoot (기존)
└── QuizTrigger (Position: 0, 0, -10) ← 새로 추가
```

---

### 9.3 QuizTrigger 컴포넌트 추가

**QuizTrigger 오브젝트 선택 후:**

1. **Add Component → Quiz Trigger**
   설정:
   - **Trigger Once**: ✅ 체크
   - **Trigger On Enter**: ✅ 체크
   - **Cooldown Time**: `5`
   - **Door Controller**: (비워둠 - 다음 단계에서 자동 연결)
   - **Trigger Size**: `(4, 5, 2)` (트랙 폭에 맞게 조정)

2. **Add Component → Box Collider**
   설정:
   - **Is Trigger**: ✅ 체크 (매우 중요!)
   - **Center**: `(0, 2.5, 0)`
   - **Size**: `(4, 5, 2)` (도로 폭에 맞게, 권장: X=3-4)

**⚠️ Box Collider Size 조정:**
- **X (가로)**: 트랙 폭과 맞춰야 함 (기본 트랙 폭 10m이면 4-10 사이로 조정)
- **Y (높이)**: 플레이어 높이보다 크게 (5m 권장)
- **Z (깊이)**: 얇게 (2m 권장, 트리거 감지 영역)

**⚠️ 사전 준비: Player에 Rigidbody가 있는지 확인!**
- Section 4.2 참고: Player에 Rigidbody 추가 (Is Kinematic = true)
- Rigidbody가 없으면 퀴즈 트리거가 **즉시 반응하지 않거나 작동하지 않음**

---

### 9.4 QuizDoorController 오브젝트 생성 (QuizTrigger의 자식)

**⚠️ 핵심:**
- QuizDoorController는 QuizTrigger의 **자식**으로 만듭니다
- 이렇게 하면 QuizTrigger.Start()가 자동으로 자식에서 QuizDoorController를 찾습니다

1. **QuizTrigger 우클릭 → Create Empty**
2. 이름: `QuizDoorController`
3. **Position**: `(0, 0, 0)` (로컬 위치 0)

4. **Add Component → Quiz Door Controller**
   설정:
   - **Quiz Doors**: Size를 **3**으로 설정 (Element 0, 1, 2가 생김)
   - 각 Element는 비워둠 (다음 단계에서 수동 연결)

**최종 구조 (StartTrackSegment):**
```
StartTrackSegment (Empty, Scale: 1, 1, 1) ⭐
├── Ground (Cube, Scale: 50, 0.2, 50)
├── ObstacleRoot
└── QuizTrigger (Position: 0, 0, -10)
    ├── (QuizTrigger 컴포넌트)
    ├── (Box Collider, Is Trigger = true)
    └── QuizDoorController (Position: 0, 0, 0)
        └── (QuizDoorController 컴포넌트, Quiz Doors: Size 3)
```

**⚠️ Scale 주의:**
- StartTrackSegment 루트는 반드시 Scale (1, 1, 1)을 유지하세요!
- Ground만 Scale (50, 0.2, 50)으로 설정
- QuizTrigger, QuizDoorController도 모두 Scale (1, 1, 1) 유지

**프리팹 저장**: Ctrl+S

---

### 9.5 DoorTrackSegment 프리팹 준비

**목적**: 실제 QuizDoor 3개를 포함하는 TrackSegment 생성

1. **Project 창**에서 **TrackSegment_01** 프리팹 복제
2. 이름 변경: `DoorTrackSegment`
3. 프리팹 더블클릭하여 편집 모드 진입

---

### 9.6 door 부모 오브젝트 생성

**DoorTrackSegment 프리팹 안에:**

1. **DoorTrackSegment 루트 우클릭 → Create Empty**
2. 이름: `door`
3. **Position**: `(0, 0, 0)` (트랙 중앙)

**구조:**
```
DoorTrackSegment (Empty, Scale: 1, 1, 1)
├── Ground (Cube, Scale: 50, 0.2, 50)
├── ObstacleRoot (기존)
└── door (Position: 0, 0, 0) ← 새로 추가
```

---

### 9.7 QuizDoor 3개 추가 (door의 자식)

**door 오브젝트 안에:**

1. **Project 창에서 QuizDoor 프리팹**을 **door 안으로 드래그** (3번)
2. 이름 변경:
   - `QuizDoor_1`
   - `QuizDoor_2`
   - `QuizDoor_3`

3. **각 문 위치 설정** (door 기준 상대 좌표):
   - **QuizDoor_1**: Position `(-15, 0, 0)` (왼쪽)
   - **QuizDoor_2**: Position `(0, 0, 0)` (중앙)
   - **QuizDoor_3**: Position `(15, 0, 0)` (오른쪽)

**최종 구조 (DoorTrackSegment):**
```
DoorTrackSegment (Empty, Scale: 1, 1, 1) ⭐
├── Ground (Cube, Scale: 50, 0.2, 50)
├── ObstacleRoot
└── door (Position: 0, 0, 0)
    ├── QuizDoor_1 (Position: -15, 0, 0)
    ├── QuizDoor_2 (Position: 0, 0, 0)
    └── QuizDoor_3 (Position: 15, 0, 0)
```

**프리팹 저장**: Ctrl+S

---

### 9.8 씬에 배치 및 수동 연결 ⭐ (핵심 단계)

**⚠️ 이 단계에서 QuizDoorController와 QuizDoor를 수동으로 연결합니다!**

#### 9.8.1 Hierarchy에 배치

1. **Project 창**에서 **StartTrackSegment**를 **Hierarchy**로 드래그
   - Position: `(0, 0, 0)` (예시)

2. **Project 창**에서 **DoorTrackSegment**를 **Hierarchy**로 드래그
   - Position: `(0, 0, 50)` (StartTrackSegment로부터 50m 떨어진 위치, 예시)

**⚠️ 위치 조정:**
- DoorTrackSegment는 플레이어가 QuizTrigger를 통과한 후 도달할 위치에 배치하세요
- 예: StartTrackSegment가 Z=0이면, DoorTrackSegment를 Z=30~50 정도에 배치

#### 9.8.2 수동 참조 연결

**Hierarchy에서:**

1. **StartTrackSegment → QuizTrigger → QuizDoorController** 오브젝트 선택

2. **Inspector에서 Quiz Door Controller 컴포넌트 찾기**

3. **Quiz Doors 배열 (Size: 3)을 펼치기**

4. **Hierarchy에서 DoorTrackSegment → door → QuizDoor_1을 찾아서:**
   - **Element 0**에 **드래그 앤 드롭**

5. **Hierarchy에서 DoorTrackSegment → door → QuizDoor_2를 찾아서:**
   - **Element 1**에 **드래그 앤 드롭**

6. **Hierarchy에서 DoorTrackSegment → door → QuizDoor_3을 찾아서:**
   - **Element 2**에 **드래그 앤 드롭**

**✅ 연결 완료 확인:**
```
Quiz Door Controller 컴포넌트:
Quiz Doors (Size: 3)
├── Element 0: QuizDoor_1 (Quiz Door)
├── Element 1: QuizDoor_2 (Quiz Door)
└── Element 2: QuizDoor_3 (Quiz Door)
```

**⚠️ 중요: Door Controller 자동 연결 확인**

7. **StartTrackSegment → QuizTrigger** 오브젝트 선택

8. **Inspector에서 Quiz Trigger 컴포넌트 확인**
   - **Door Controller** 필드에 `QuizDoorController`가 자동으로 연결되어 있는지 확인
   - 비어있다면: `QuizDoorController` 오브젝트를 수동으로 드래그

---

### 9.9 자동 연결 vs 수동 연결 정리

**자동으로 연결되는 것:**
- ✅ QuizTrigger → QuizDoorController (자식이므로 `GetComponentInChildren()` 사용)
- ❌ QuizDoorController → QuizDoor 3개 (별도 TrackSegment에 있으므로 자동 연결 불가)

**수동으로 연결해야 하는 것:**
- ⚠️ QuizDoorController의 Quiz Doors 배열 (Element 0, 1, 2)
  - Hierarchy에서 DoorTrackSegment/door/QuizDoor_1, 2, 3를 직접 드래그

**자동 연결 원리:**
- QuizTrigger는 `Start()`에서 `GetComponentInChildren<QuizDoorController>()`로 **자식**만 탐색
- QuizDoorController는 `Awake()`에서 `GetComponentsInChildren<QuizDoor>()`로 **자식**만 탐색
- 별도 TrackSegment에 있는 문은 자식이 아니므로 **수동 연결 필수**

---

### 9.10 QuizTrigger 시각화 (선택사항)

플레이 테스트 시 QuizTrigger 위치를 보기 위해 시각적 표시를 추가할 수 있습니다.

**StartTrackSegment 프리팹 편집 모드에서:**

1. **QuizTrigger 우클릭 → 3D Object → Cube**
2. 이름: `Visual`
3. 설정:
   - Position: `(0, 2.5, 0)` (로컬)
   - Scale: `(4, 5, 0.2)` (얇은 벽)
   - Material: 노란색, 반투명 (Alpha 77)
   - **Remove Component → Box Collider** (Cube의 Collider 제거, QuizTrigger의 Collider만 사용)

**⚠️ Visual 위치 주의:**
- Visual의 Position은 Box Collider의 Center와 맞춰야 합니다
- 예: Box Collider Center가 (0, 2.5, 0)이면 Visual Position도 (0, 2.5, 0)

---

### 9.11 여러 퀴즈 위치 만들기

**방법 1: 씬에서 여러 세트 배치**
1. **StartTrackSegment**와 **DoorTrackSegment**를 여러 번 배치
2. 각 세트마다 수동으로 QuizDoorController → QuizDoor 참조 연결
3. 예시:
   - 첫 번째 퀴즈: StartTrackSegment (Z=0) + DoorTrackSegment (Z=50)
   - 두 번째 퀴즈: StartTrackSegment (Z=100) + DoorTrackSegment (Z=150)

**방법 2: 프리팹 변형 생성 (Prefab Variant)**
1. StartTrackSegment, DoorTrackSegment를 씬에 배치하고 연결
2. 연결된 상태 그대로 두 세그먼트를 하나의 부모 오브젝트 아래로 그룹화
3. 이 그룹을 프리팹으로 저장: `QuizSet_01`
4. 이후 `QuizSet_01`을 배치하면 연결 상태가 유지됨

**⚠️ 핵심 장점:**
- **여러 퀴즈 위치**: 맵에 원하는 만큼 퀴즈 위치 배치 가능
- **독립적 동작**: 각 QuizTrigger가 자신의 문 세트만 관리
- **간섭 없음**: QuizTrigger_1과 QuizTrigger_2가 서로 영향을 주지 않음
- **유연한 배치**: 트리거와 문 위치를 자유롭게 조정 가능

**⚠️ 주의사항:**
- 각 퀴즈 세트마다 반드시 QuizDoorController → QuizDoor 3개 수동 연결 필요
- 프리팹을 복제하면 참조가 끊어지므로 재연결 필요

---

### 9.12 동작 방식

**런타임 동작:**
1. 플레이어가 **StartTrackSegment의 QuizTrigger** 통과
2. QuizTrigger가 QuizManager에게 자신의 QuizDoorController 전달
3. QuizManager가 퀴즈 시작 (질문 표시, **게임은 계속 진행**)
4. QuizManager가 **해당 QuizDoorController**에 퀴즈 데이터 할당
5. QuizDoorController가 **연결된 DoorTrackSegment의 3개 문**에 정답/오답 랜덤 할당
6. 플레이어가 DoorTrackSegment 도달 후 문 선택:
   - **정답 문**: 통과, +5초, 타이머 초록색 표시, 1초 후 문 리셋
   - **오답 문**: 충돌, -5초 (한 번만), 빨간색 표시, 재도전 가능
7. 정답 후 1초 뒤 **해당 QuizDoorController** 비활성화 (문 숨김)

**다른 퀴즈 위치:**
- 플레이어가 두 번째 StartTrackSegment 통과 → 두 번째 DoorTrackSegment의 문 세트에만 퀴즈 할당
- 각 퀴즈 세트는 독립적으로 동작

**⚠️ 중요 변경사항:**
- **게임 일시정지 제거**: 퀴즈가 나와도 플레이어는 계속 이동 가능
- **퀴즈 중복 방지**: 한 게임에서 같은 퀴즈는 한 번만 출제
- **모든 퀴즈 완료 시**: 더 이상 퀴즈가 나오지 않음 (자동 리셋 없음)

---

### 9.13 하이브리드 체인 설정 ⭐ NEW (정답 시 자동 퀴즈 활성화)

**💡 하이브리드 체인이란?**
- **첫 번째 퀴즈만** QuizTrigger 필요
- 정답 문 통과 시 **다음 QuizDoorController 자동 활성화**
- QuizTrigger를 여러 개 배치할 필요 없이 자동으로 연결됨

**장점:**
- ✅ QuizTrigger 1개만 배치 (첫 퀴즈용)
- ✅ 정답 → 다음 퀴즈 자동 시작
- ✅ 레벨 디자인 간소화
- ✅ 퀴즈 흐름 자연스러움

---

#### 9.13.1 체인 구조 예시

```
QuizZone_1 (첫 번째만 QuizTrigger 필요)
├─ QuizTrigger ← 플레이어가 처음 지나갈 때만 필요
└─ DoorController_1
   ├─ Inspector: Next Door Controller = DoorController_2 ⭐
   └─ Door 3개 (QuizDoor_1, 2, 3)

QuizZone_2 (QuizTrigger 없음!)
└─ DoorController_2
   ├─ Inspector: Next Door Controller = DoorController_3 ⭐
   └─ Door 3개 (QuizDoor_1, 2, 3)

QuizZone_3 (마지막)
└─ DoorController_3
   ├─ Inspector: Next Door Controller = None ⭐ (비워둠)
   └─ Door 3개 (QuizDoor_1, 2, 3)
```

---

#### 9.13.2 씬 구조 설정 (예시)

**1단계: 첫 번째 퀴즈 존 (QuizTrigger 필요)**

Hierarchy에 다음과 같이 배치:

```
Track (Empty GameObject) - 전체 트랙 루트
│
├─ QuizZone_1 (Empty GameObject)
│  ├─ QuizTrigger (Box Collider, QuizTrigger.cs)
│  │  └─ DoorController_1 (QuizDoorController.cs)
│  │     └─ Inspector: Next Door Controller = DoorController_2 연결 ⭐
│  │
│  └─ Doors_1 (Empty GameObject) - 문 그룹
│     ├─ QuizDoor_1 (문 3D 모델 + QuizDoor.cs + BoxCollider)
│     ├─ QuizDoor_2
│     └─ QuizDoor_3
│
├─ QuizZone_2 (Empty GameObject) - QuizTrigger 없음!
│  └─ DoorController_2 (QuizDoorController.cs)
│     ├─ Inspector: Next Door Controller = DoorController_3 연결 ⭐
│     └─ Doors_2 (자식)
│        ├─ QuizDoor_1
│        ├─ QuizDoor_2
│        └─ QuizDoor_3
│
└─ QuizZone_3 (Empty GameObject) - 마지막 퀴즈
   └─ DoorController_3 (QuizDoorController.cs)
      ├─ Inspector: Next Door Controller = None (비워둠) ⭐
      └─ Doors_3 (자식)
         ├─ QuizDoor_1
         ├─ QuizDoor_2
         └─ QuizDoor_3
```

---

#### 9.13.3 Inspector 설정 (핵심!)

각 **QuizDoorController** 선택 후 Inspector에서:

**DoorController_1:**
```
Quiz Door Controller (Script)
├─ Quiz Doors (Size: 3)
│  ├─ Element 0: QuizDoor_1 (드래그)
│  ├─ Element 1: QuizDoor_2 (드래그)
│  └─ Element 2: QuizDoor_3 (드래그)
│
└─ Chain Settings (Optional)
   └─ Next Door Controller: DoorController_2 ⭐ (드래그)
```

**DoorController_2:**
```
Quiz Door Controller (Script)
├─ Quiz Doors (Size: 3)
│  └─ ... (문 3개 연결)
│
└─ Chain Settings (Optional)
   └─ Next Door Controller: DoorController_3 ⭐ (드래그)
```

**DoorController_3 (마지막):**
```
Quiz Door Controller (Script)
├─ Quiz Doors (Size: 3)
│  └─ ... (문 3개 연결)
│
└─ Chain Settings (Optional)
   └─ Next Door Controller: None ⭐ (비워둠)
```

---

#### 9.13.4 작동 흐름

```
1. 플레이어가 QuizTrigger 통과
   ↓
2. DoorController_1 활성화 → Door 3개에 퀴즈 할당
   ↓
3. 플레이어가 정답 Door 통과
   ↓ (+5초, 점수 +1)
4. 1.5초 후 자동으로 DoorController_2 활성화 ⭐
   ↓
5. DoorController_2의 Door 3개에 새 퀴즈 할당
   ↓
6. 플레이어가 정답 Door 통과
   ↓ (+5초, 점수 +1)
7. 1.5초 후 자동으로 DoorController_3 활성화 ⭐
   ↓
8. DoorController_3의 Door 3개에 새 퀴즈 할당
   ↓
9. 플레이어가 정답 Door 통과
   ↓ (+5초, 점수 +1)
10. Next Door Controller가 None → 체인 종료 ✅
```

**퀴즈가 더 이상 나오지 않습니다!**

---

#### 9.13.5 QuizTrigger vs 체인 비교

**기존 방식 (QuizTrigger 여러 개):**
```
QuizTrigger_1 → DoorController_1
QuizTrigger_2 → DoorController_2
QuizTrigger_3 → DoorController_3
```
- 각 퀴즈마다 QuizTrigger 필요
- 플레이어가 특정 위치 통과 시 퀴즈 시작

**하이브리드 체인 방식:**
```
QuizTrigger_1 → DoorController_1
                     ↓ (자동)
                DoorController_2
                     ↓ (자동)
                DoorController_3
```
- 첫 QuizTrigger만 필요
- 정답 → 자동으로 다음 퀴즈

---

#### 9.13.6 체크리스트

**각 QuizDoorController 설정 확인:**
- [ ] Quiz Doors 배열에 3개 문 연결됨
- [ ] Next Door Controller에 다음 컨트롤러 연결됨 (마지막 제외)
- [ ] 마지막 컨트롤러는 Next Door Controller = None

**첫 QuizZone만:**
- [ ] QuizTrigger 오브젝트 있음
- [ ] QuizTrigger의 Door Controller에 DoorController 연결됨
- [ ] Box Collider의 Is Trigger = true

**퀴즈 JSON 설정:**
- [ ] 퀴즈 개수 ≥ QuizDoorController 개수 (권장)
- [ ] 예: DoorController 3개 → 최소 퀴즈 3개 필요

---

#### 9.13.7 퀴즈 종료 조건

**체인이 종료되는 경우:**

1. **Next Door Controller = None** (권장)
   - 마지막 QuizDoorController에서 Next를 비워둠
   - 정답 통과 후 더 이상 퀴즈 없음

2. **퀴즈 소진** (자동 안전장치)
   - quiz_data.json의 모든 퀴즈를 다 사용함
   - QuizManager가 자동으로 차단
   - 콘솔 메시지: "All quizzes completed! No more quizzes available."

**권장 설정:**
- **퀴즈 개수 ≥ DoorController 개수**
- 예: DoorController 5개 → 퀴즈 5개 이상 준비

---

#### 9.13.8 디버깅

**콘솔 메시지로 체인 확인:**

```
[QuizTrigger] ✅ Quiz started successfully!
[QuizDoorController] Assigned quiz to 3 doors
[QuizDoor] Correct! Player entered door 1: 서울
[QuizDoorController] Activating next controller: DoorController_2 ⭐
[QuizDoorController] Assigned quiz to 3 doors
...
```

**문제 해결:**
- "Activating next controller" 메시지가 안 나오면?
  → Next Door Controller 연결 확인
- 체인이 작동하지 않으면?
  → DoorController_1, 2, 3이 모두 Hierarchy에 있는지 확인
  → Quiz Doors 배열에 문 3개 제대로 연결되었는지 확인

---

### 9.14 현재 시스템 구조 정리 (하이브리드 체인 방식) ⭐

**현재 사용 중인 방식:**

1. **첫 QuizZone**: QuizTrigger + DoorController_1 (자식) + Doors (3개)
2. **나머지 QuizZone**: DoorController만 + Doors (3개) - QuizTrigger 없음!
3. **하이브리드 체인**: Next Door Controller로 연결 (1 → 2 → 3 → None)
4. **수동 연결**: 각 DoorController의 Quiz Doors 배열에 문 3개 드래그

**장점:**
- **QuizTrigger 1개만**: 첫 퀴즈만 트리거 필요, 나머지는 자동 활성화
- **자동 퀴즈 흐름**: 정답 → 1.5초 후 다음 퀴즈 자동 시작
- **간단한 구조**: 각 QuizZone마다 DoorController + Doors만 배치
- **유연한 배치**: 문 위치를 자유롭게 배치 가능

**구조 비교:**
```
[이전] Managers 싱글톤 방식 (제거됨)
Managers
└── QuizDoorController ← 모든 문 전역 관리 (작동 안 함)

[하이브리드 체인] 현재 방식 ⭐
QuizZone_1 (첫 번째만 QuizTrigger)
├─ QuizTrigger
│  └─ DoorController_1 (자식)
│     └─ Inspector: Next = DoorController_2
└─ Doors (3개)

QuizZone_2 (QuizTrigger 없음!)
├─ DoorController_2
│  └─ Inspector: Next = DoorController_3
└─ Doors (3개)

QuizZone_3 (마지막)
├─ DoorController_3
│  └─ Inspector: Next = None
└─ Doors (3개)

체인: Trigger → Door1 정답 → (자동 1.5초 후) → Door2 정답 → Door3 ...
```

**핵심 차이점:**
- **이전**: Managers에 QuizDoorController (작동 안 함, 제거됨)
- **현재**: QuizTrigger의 자식 + 체인 연결 (하이브리드 방식)
- **이유**: 트리거와 문이 별도 TrackSegment에 있어서 자식 관계가 아니기 때문

---

## 10. Obstacle 프리팹 생성

### 10.1 Box Obstacle
1. **Hierarchy 우클릭 → 3D Object → Cube**
2. 이름: `Obstacle_Box`
3. 설정:
   - Position: `(0, 0.5, 0)`
   - Scale: `(1, 1, 1)`
   - Tag: `Obstacle`

### 10.2 Collider 설정
**Box Collider 컴포넌트:**
- **Is Trigger**: 체크
- Center: `(0, 0, 0)`
- Size: `(1, 1, 1)`

### 10.3 ObstacleController 추가
**Add Component → Obstacle Controller**

설정:
- **Rotate**: 체크
- **Rotation Speed**: `(0, 50, 0)`
- **Move**: 체크 해제

### 10.4 Material 생성
1. **Project → Create → Material → `ObstacleMaterial`**
2. 색상: 빨간색
3. Obstacle_Box의 Mesh Renderer에 적용

### 10.5 Prefab 저장
1. **`Assets/Prefabs/Obstacles/` 폴더 생성**
2. **Obstacle_Box를 폴더로 드래그**
3. **Hierarchy에서 삭제**

### 10.6 추가 Obstacle 생성 (선택사항)
- `Obstacle_Sphere` (Sphere로 생성)
- `Obstacle_Cylinder` (Cylinder로 생성)
- `Obstacle_Wall` (Cube, Scale Z를 크게)


### 10.7 날아가는 장애물 시스템 ⭐ NEW

ObstacleController에 다양한 날아가기 모드가 추가되었습니다!

#### 🎯 Fly Mode 종류

**1. None (기본)**
- 날아가지 않음
- 왕복 이동(Move)과 회전(Rotate)만 사용

**2. Projectile (발사형)**
- 설정한 방향으로 직선 이동
- 예: 화살, 총알처럼 날아가는 장애물

**3. TargetPlayer (플레이어 추적형)**
- 게임 시작 시 플레이어 위치를 감지
- 플레이어를 향해 일직선으로 날아감
- 장애물이 자동으로 플레이어 방향으로 회전

**4. LaneRush (레인 돌진형)** ⭐ 템플런 스타일
- 3개 레인 중 하나에서 플레이어를 향해 달려옴
- X축 위치는 레인에 고정, Z축으로만 이동
- 플레이어는 좌우로만 피할 수 있음

**5. Float (부유형)**
- 앞으로 이동하면서 위아래로 떠다님
- 새처럼 날아가는 효과

**6. Wave (파도형)**
- 앞으로 이동하면서 좌우로 물결침
- 뱀처럼 구불구불 날아가는 효과

**7. Circle (원형)**
- 원을 그리며 이동
- 회전하면서 날아가는 효과

---

### 10.8 레인 장애물 설정

#### 레인 시스템 구조
```
트랙이 3개 레인으로 나뉩니다:
- 레인 0 = 왼쪽 (X = -3)
- 레인 1 = 중앙 (X = 0)
- 레인 2 = 오른쪽 (X = +3)
```

#### 단일 레인 장애물 만들기

1. **Obstacle 프리팹 선택**
2. **ObstacleController 설정:**
   ```
   Flying Settings:
   ├─ Fly Mode: LaneRush
   ├─ Destroy On Distance: ✓ 체크
   └─ Max Distance: 100
   
   Lane Rush Settings:
   ├─ Lane Index: 1 (0=왼쪽, 1=중앙, 2=오른쪽)
   ├─ Lane Width: 3
   └─ Rush Speed: 15
   ```

#### 여러 레인 동시에 막기

**2개 레인 패턴:**
1. 빈 GameObject 생성: `Pattern_Double`
2. 두 개의 장애물 자식으로 추가:
   - Obstacle1: Lane Index = 0 (왼쪽)
   - Obstacle2: Lane Index = 1 (중앙)
3. 플레이어는 오른쪽(Lane 2)으로 피해야 함

**3개 레인 패턴 (점프 필요):**
1. 빈 GameObject 생성: `Pattern_Triple`
2. 세 개의 장애물 자식으로 추가:
   - Obstacle1: Lane Index = 0
   - Obstacle2: Lane Index = 1
   - Obstacle3: Lane Index = 2
3. 플레이어는 점프로 피해야 함

---

### 10.9 자동 레인 장애물 생성기 ⭐ NEW

#### LaneObstacleSpawner 설정

1. **빈 GameObject 생성**
   - 이름: `LaneObstacleSpawner`
   - Position: `(0, 0, 0)`

2. **Add Component → Lane Obstacle Spawner**

3. **Inspector 설정:**
   ```
   Spawner Settings:
   ├─ Auto Spawn: ✓ 체크
   ├─ Spawn Interval: 2.5 (생성 간격 초)
   ├─ Spawn Distance: 50 (플레이어 앞쪽 거리)
   └─ Spawn Height: 1
   
   Obstacle Prefab:
   ├─ Obstacle Prefab: Obstacle_Box (드래그)
   └─ Obstacle Rush Speed: 15
   
   Lane Settings:
   ├─ Lane Width: 3
   ├─ Min Lanes: 1 (최소 생성 개수)
   └─ Max Lanes: 2 (최대 생성 개수)
   
   Pattern Settings:
   ├─ Use Patterns: ✓ 체크
   └─ Spawn Patterns: (패턴 배열)
   ```

4. **Spawn Patterns 설정 (Size: 6):**
   ```
   Element 0:
   ├─ Pattern Name: "Single_Left"
   ├─ Lanes: Size(1) → 0
   └─ Probability: 0.2
   
   Element 1:
   ├─ Pattern Name: "Single_Center"
   ├─ Lanes: Size(1) → 1
   └─ Probability: 0.2
   
   Element 2:
   ├─ Pattern Name: "Single_Right"
   ├─ Lanes: Size(1) → 2
   └─ Probability: 0.2
   
   Element 3:
   ├─ Pattern Name: "Double_LeftCenter"
   ├─ Lanes: Size(2) → 0, 1
   └─ Probability: 0.15
   
   Element 4:
   ├─ Pattern Name: "Double_CenterRight"
   ├─ Lanes: Size(2) → 1, 2
   └─ Probability: 0.15
   
   Element 5:
   ├─ Pattern Name: "Double_LeftRight"
   ├─ Lanes: Size(2) → 0, 2
   └─ Probability: 0.1
   ```

#### 작동 방식
- 2.5초마다 자동으로 장애물 생성
- 패턴 확률에 따라 1~2개 레인에 장애물 생성
- 플레이어 뒤로 지나간 장애물은 자동 제거
- 생성된 장애물은 LaneObstacleSpawner의 자식으로 관리

---

### 10.10 장애물 배치 예시

#### 초급 구간
```
TrackSegment_Easy:
└─ ObstaclePatterns:
    ├─ Pattern_Single_Center (Z=20)
    ├─ Pattern_Single_Left (Z=35)
    └─ Pattern_Single_Right (Z=50)
```

#### 중급 구간
```
TrackSegment_Medium:
└─ ObstaclePatterns:
    ├─ Pattern_Double_LeftCenter (Z=20)
    ├─ Pattern_Double_CenterRight (Z=40)
    └─ Pattern_Single_Center (Z=60)
```

#### 고급 구간
```
TrackSegment_Hard:
└─ ObstaclePatterns:
    ├─ Pattern_Triple_All (Z=20) ← 점프 필요
    ├─ Pattern_Double_LeftRight (Z=40)
    └─ Pattern_Zigzag (Z=60) ← 시간차 공격
```

#### 시간차 공격 패턴 (Zigzag)
```
Pattern_Zigzag:
├─ Obstacle1 (Z=60, Lane=0, Rush Speed=15)
├─ Obstacle2 (Z=55, Lane=1, Rush Speed=15)
└─ Obstacle3 (Z=50, Lane=2, Rush Speed=15)
```

---

### 10.11 난이도별 권장 설정

**쉬움 (초보자용):**
```
Rush Speed: 10
Spawn Interval: 3.0
Min Lanes: 1
Max Lanes: 1
```

**보통:**
```
Rush Speed: 15
Spawn Interval: 2.5
Min Lanes: 1
Max Lanes: 2
```

**어려움:**
```
Rush Speed: 20
Spawn Interval: 2.0
Min Lanes: 1
Max Lanes: 2
```

**매우 어려움:**
```
Rush Speed: 25
Spawn Interval: 1.5
Min Lanes: 2
Max Lanes: 3
Lane Width: 2 (좁은 레인)
```

---

### 10.12 기타 Fly Mode 예시

#### TargetPlayer (플레이어 추적)
```
Fly Mode: TargetPlayer
Fly Speed: 8
Activation Delay: 0.5
Destroy On Distance: ✓
Max Distance: 100
```

#### Float (부유형)
```
Fly Mode: Float
Fly Direction: (0, 0, 1)
Fly Speed: 5
Float Amplitude: 2
Float Frequency: 1
```

#### Wave (파도형)
```
Fly Mode: Wave
Fly Direction: (0, 0, 1)
Fly Speed: 6
Wave Amplitude: 3
Wave Frequency: 2
```

---
## 11. UI 구성

### 11.1 Canvas 설정
**Canvas 선택**

설정:
- **Render Mode**: Screen Space - Overlay
- **Canvas Scaler**:
  - UI Scale Mode: Scale With Screen Size
  - Reference Resolution: `1920 x 1080`
  - Match: `0.5`

---

### 10.2 HUD Panel 생성

**Canvas 우클릭 → UI → Panel**

1. 이름: `HUD Panel`
2. Color: 투명 (Alpha 0)

---

#### ScoreText
**HUD Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `ScoreText`
2. Rect Transform:
   - Anchor: Top Left
   - Pos: `(150, -30)`
   - Size: `(200, 40)`
3. TextMeshPro:
   - Text: `"점수: 0"`
   - Font Size: `24`
   - Color: 흰색
   - Alignment: Left

---

#### DistanceText
**HUD Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `DistanceText`
2. Rect Transform:
   - Anchor: Top Left
   - Pos: `(150, -70)`
   - Size: `(200, 40)`
3. Text: `"거리: 0m"`

---


#### GameTimerText ⭐ (100초 타이머)
**HUD Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `GameTimerText`
2. Rect Transform:
   - Anchor: **Top Center**
   - Pos: `(0, -30)`
   - Size: `(300, 60)`
3. TextMeshPro:
   - Text: `"제한시간: 01:40"`
   - Font Size: `36`
   - Color: 흰색
   - Alignment: **Center**
   - Font Style: **Bold**

**기능:**
- 100초부터 카운트다운
- 10초 이하: 빨간색
- 30초 이하: 노란색
- 정답 시 +5초, 오답 시 -5초

---

#### DashGauge ⭐ (대쉬 게이지)
**HUD Panel 우클릭 → UI → Image**

1. 이름: `DashGauge`
2. Rect Transform:
   - Anchor: **Top Left**
   - Pos: `(150, -150)`
   - Size: `(200, 30)`
3. Image:
   - **Source Image**: `TempDashGauge` (없으면 UI용 Sprite 아무거나)
   - **Image Type**: Filled
   - **Fill Method**: Horizontal
   - **Fill Origin**: Left
   - Color: 흰색
   - **Raycast Target**: 체크 해제 (HUD 클릭 방지)

**기능:**
- Z 키 누르는 동안 fillAmount 감소
- 게이지 소진 시 회색, 있을 때 흰색

---

### 10.3 Quiz Panel 생성 ⭐

**Canvas 우클릭 → UI → Panel**

1. 이름: `Quiz Panel`
2. Color: 반투명 검정 `(0, 0, 0, 200)`
3. **초기 상태: 비활성화** (체크 해제)

---

#### QuestionText (질문만 3초 표시)
**Quiz Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `QuestionText`
2. Rect Transform:
   - Anchor: Center
   - Pos: `(0, 0)`
   - Size: `(1000, 200)`
3. TextMeshPro:
   - Text: `"질문이 여기에 표시됩니다"`
   - Font Size: `48`
   - Alignment: Center
   - Wrapping: Enabled
   - Color: 흰색
   - Font Style: Bold

**⚠️ 중요:**
- **버튼은 만들지 않습니다!** (Choice Buttons/Texts는 Size 0)
- 질문만 3초 표시 후 자동으로 숨김
- QuizDoorController가 Unity에 배치된 3개 문에 정답/오답 데이터를 할당 (생성 X)
- 플레이어가 문을 통과하면 답안 선택

---

### 10.4 Result Panel 생성

**Canvas 우클릭 → UI → Panel**

1. 이름: `Result Panel`
2. Color: `(0, 0, 0, 230)`
3. **초기 상태: 비활성화**

---

#### TitleText
**Result Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `TitleText`
2. Pos: `(0, 300)`
3. Size: `(600, 100)`
4. Text: `"게임 결과"`
5. Font Size: `48`

---

#### ResultScoreText
**Result Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `ResultScoreText`
2. Pos: `(0, 150)`
3. Size: `(400, 50)`
4. Text: `"점수: 0"`
5. Font Size: `32`

---

#### ResultDistanceText
- Pos Y: `90`
- Text: `"거리: 0m"`

#### ResultTimeText
- Pos Y: `30`
- Text: `"시간: 00:00"`

#### ResultCorrectText
- Pos Y: `-30`
- Text: `"정답: 0"`
- Color: **Green**

#### ResultWrongText
- Pos Y: `-90`
- Text: `"오답: 0"`
- Color: **Red**

---

#### RestartButton
**Result Panel 우클릭 → UI → Button - TextMeshPro**

**Step 1: 버튼 생성 및 기본 설정**
1. Hierarchy에서 **Result Panel 우클릭** → UI → Button - TextMeshPro
2. 이름을 `RestartButton`으로 변경

**Step 2: Rect Transform 설정 (위치/크기)**
```
Inspector → Rect Transform
├─ Anchor Presets: Center-Middle (중앙 정렬)
├─ Pos X: 0
├─ Pos Y: -200
├─ Pos Z: 0
├─ Width: 300
├─ Height: 60
└─ Scale: (1, 1, 1)
```

**Step 3: Image 컴포넌트 (버튼 배경색)**
```
Inspector → Image
├─ Color: 흰색 또는 원하는 색
└─ Material: None (Material)
```

**Step 4: Button 컴포넌트 (클릭 이벤트)**
```
Inspector → Button
├─ Interactable: ✅ 체크
├─ Transition: Color Tint
├─ Target Graphic: RestartButton (Image) 
├─ Normal Color: 흰색
├─ Highlighted Color: 밝은 회색
├─ Pressed Color: 진한 회색
└─ On Click ()
    ├─ ➕ 버튼 클릭 (이벤트 추가)
    ├─ None (Object): GameStateManager 드래그 ⭐
    └─ Function: GameStateManager → RestartGame() 선택 ⭐
```

**⚠️ 중요: On Click 이벤트 설정 방법**
1. **On Click ()** 아래 **+** 버튼 클릭
2. **None (Object)** 칸이 나타남
3. Hierarchy에서 **GameStateManager** 찾기
4. **GameStateManager**를 **None (Object)** 칸으로 드래그
5. 드롭다운에서 **GameStateManager → RestartGame()** 선택

**Step 5: 자식 Text 설정 (버튼 텍스트)**
```
Hierarchy → RestartButton 펼치기
└─ Text (TMP) 선택

Inspector → TextMeshPro - Text (UI)
├─ Text: "다시 시작"
├─ Font Size: 28
├─ Color: 검정색
├─ Alignment: Center (가운데 정렬)
└─ Auto Size: ❌ (체크 해제)
```

**✅ 최종 체크리스트:**
- [ ] Pos Y = -200
- [ ] Size = 300 x 60
- [ ] On Click 이벤트에 GameStateManager.RestartGame() 연결됨
- [ ] 자식 Text = "다시 시작" (Font Size 28)
- [ ] 클릭하면 게임 재시작됨

---

#### QuitButton
**RestartButton 복사해서 만들기**

**Step 1: 버튼 복사**
1. Hierarchy에서 **RestartButton** 선택
2. **Ctrl+D** (복제) 또는 우클릭 → Duplicate
3. 이름을 `QuitButton`으로 변경

**Step 2: Rect Transform 수정**
```
Inspector → Rect Transform
└─ Pos Y: -280 으로 변경 ⭐ (RestartButton 아래)
```

**Step 3: Button 컴포넌트 (클릭 이벤트 변경)**
```
Inspector → Button → On Click ()
├─ None (Object): GameStateManager (그대로)
└─ Function: GameStateManager → QuitGame() 선택 ⭐
```

**💡 QuitGame() 메서드란?**
- GameStateManager에 추가된 메서드로, 게임을 종료합니다
- Unity 에디터에서는 Play 모드를 중지합니다
- 빌드된 게임에서는 Application.Quit()을 호출합니다

**Step 4: 자식 Text 수정**
```
Hierarchy → QuitButton 펼치기
└─ Text (TMP) 선택

Inspector → TextMeshPro - Text (UI)
└─ Text: "종료" 로 변경 ⭐
```

**✅ 최종 체크리스트:**
- [ ] Pos Y = -280
- [ ] Size = 300 x 60 (RestartButton과 동일)
- [ ] On Click 이벤트에 GameStateManager.QuitGame() 연결됨 ✅
- [ ] 자식 Text = "종료" (Font Size 28)
- [ ] 클릭하면 게임 종료됨 (에디터: Play 모드 중지)

---

### 10.5 GameOver Panel (선택사항)

**Canvas 우클릭 → UI → Panel**

1. 이름: `GameOver Panel`
2. Color: `(128, 0, 0, 204)` (붉은색)
3. **초기 상태: 비활성화**

---

#### GameOverText
**GameOver Panel 우클릭 → UI → Text - TextMeshPro**

1. 이름: `GameOverText`
2. Rect Transform:
   - Anchor: Center
   - Pos: `(0, 0)`
   - Size: `(600, 100)`
3. TextMeshPro:
   - Text: `"게임 오버"`
   - Font Size: `48`
   - Color: 흰색
   - Alignment: Center
   - Font Style: Bold

---

## 12. 참조 연결

### 12.1 SegmentManager 연결

**Managers/SegmentManager 선택**

**주의:** SegmentManager는 싱글톤 Instance만 제공하므로 연결할 항목이 없습니다.
- 자동 트랙/장애물 생성 기능이 제거되었습니다.
- Unity에서 수동으로 배치한 트랙을 사용합니다.

---

### 12.2 QuizManager 연결 ⭐

퀴즈 시스템이 제대로 작동하려면 QuizManager에 JSON 파일을 연결해야 합니다.

**Managers 오브젝트 선택 → QuizManager 컴포넌트 찾기**

1. **Quiz Json File** 슬롯 확인
2. **Project 창에서 `Assets/Resources/quizzes` 찾기** (확장자 .json 없이 표시됨)
3. **quizzes 파일을 Quiz Json File 슬롯에 드래그**

**✅ 올바른 설정:**
- Quiz Json File: `quizzes` (Resources 폴더 안의 파일)
- Shuffle Quizzes: ✅ 체크 (퀴즈 순서 섞기)

**❌ 흔한 실수:**
- Quiz Json File이 비어있음 → 퀴즈 로드 실패, 샘플 퀴즈만 2개 표시
- JSON 파일이 Resources 폴더 밖에 있음 → 런타임 로드 실패

---

### 12.3 UIManager 연결 (전체 UI 시스템) ⭐⭐⭐

**이 부분이 가장 중요합니다!** UIManager는 게임의 모든 UI를 관리합니다:
- **HUD**: 점수, 거리, 타이머, 대쉬 게이지
- **Quiz Panel**: 퀴즈 질문 표시
- **Result Panel**: 게임 종료 시 결과 화면
- **GameOver Panel**: 타임오버 시 게임오버 화면

UI가 안 보이는 문제의 90%가 이 연결 누락 때문입니다.

---

#### 단계 1: UIManager 컴포넌트 추가

1. **Hierarchy → Canvas 선택** (Managers가 아님!)
2. **Inspector 창 하단 → Add Component 클릭**
3. **"UI Manager" 검색 → 추가**

**⚠️ 주의:**
- UIManager는 **Canvas**에 붙입니다
- Canvas에 이미 있으면 추가하지 마세요 (중복 방지)
- UIManager 컴포넌트가 보이면 성공

---

#### 단계 2: Panels 연결

UIManager 컴포넌트에서 다음 필드를 찾아 연결:

**Panels (4개):**

1. **HUD Panel**:
   - Hierarchy에서 `Canvas/HUD Panel` 찾기
   - UIManager의 **HUD Panel** 슬롯에 드래그

2. **Quiz Panel**:
   - Hierarchy에서 `Canvas/Quiz Panel` 찾기
   - UIManager의 **Quiz Panel** 슬롯에 드래그
   - ⚠️ Quiz Panel은 초기 상태가 **비활성화**(회색)되어 있어야 정상

3. **Result Panel**:
   - Hierarchy에서 `Canvas/Result Panel` 찾기
   - UIManager의 **Result Panel** 슬롯에 드래그
   - ⚠️ 초기 상태 비활성화

4. **Game Over Panel** (선택사항):
   - Hierarchy에서 `Canvas/GameOver Panel` 찾기
   - UIManager의 **Game Over Panel** 슬롯에 드래그
   - ⚠️ 초기 상태 비활성화

---

#### 단계 3: HUD Elements 연결 (게임 중 항상 표시되는 UI)

**HUD Panel**을 펼쳐서 자식 오브젝트들을 연결합니다.

**3-1. Score Text (점수 표시)**
   - **위치**: `Canvas → HUD Panel → ScoreText`
   - **연결**: Hierarchy에서 ScoreText를 찾아 UIManager의 **Score Text** 슬롯에 드래그
   - **역할**: 정답 개수 표시 (예: "점수: 5")
   - **표시 위치**: 화면 좌상단

**3-2. Distance Text (거리 표시)**
   - **위치**: `Canvas → HUD Panel → DistanceText`
   - **연결**: UIManager의 **Distance Text** 슬롯에 드래그
   - **역할**: 플레이어가 달린 거리 표시 (예: "거리: 123m")
   - **표시 위치**: 화면 좌상단 (ScoreText 아래)

**3-3. Game Timer Text (제한시간 타이머)** ⭐
   - **위치**: `Canvas → HUD Panel → GameTimerText`
   - **연결**: UIManager의 **Game Timer Text** 슬롯에 드래그
   - **역할**: 100초 카운트다운 타이머 (예: "제한시간: 01:35")
   - **표시 위치**: 화면 상단 중앙
   - ⚠️ **이게 없으면 타이머가 안 보입니다!**

**3-4. Dash Gauge Fill Image (대쉬 게이지)** ⭐
   - **위치**: `Canvas → HUD Panel → DashGauge`
   - **연결**: UIManager의 **Dash Gauge Fill Image** 슬롯에 드래그
   - **역할**: Z 키 대쉬 게이지 표시 (fillAmount로 게이지 감소/회복 표현)
   - **표시 위치**: 화면 좌상단
   - ⚠️ **Image** 컴포넌트가 있는 오브젝트를 드래그해야 합니다

**HUD 연결 확인:**
- [ ] Score Text 연결됨
- [ ] Distance Text 연결됨
- [ ] Game Timer Text 연결됨 (타이머)
- [ ] Dash Gauge Fill Image 연결됨 (게이지)

---

#### 단계 4: Quiz Panel Elements 연결 (퀴즈 화면)

**Quiz Panel**을 펼쳐서 퀴즈 UI를 연결합니다.

**4-1. Question Text (퀴즈 질문 표시)** ⭐⭐⭐
   - **위치**: `Canvas → Quiz Panel → QuestionText`
   - **연결**: UIManager의 **Question Text** 슬롯에 드래그
   - **역할**: 퀴즈 질문을 3초간 화면 중앙에 표시
   - **표시 예**: "대한민국의 수도는?"
   - ⚠️ **가장 중요!** 이게 없으면 퀴즈 질문이 안 보입니다!

**확인 사항:**
- QuestionText는 **TextMeshProUGUI** 컴포넌트를 가져야 합니다
- 일반 Text 컴포넌트가 아닙니다!
- Canvas → UI → Text - TextMeshPro로 생성했는지 확인

**※ 참고:**
- **Choice Buttons, Choice Texts**: 사용하지 않음 (3D 문으로 답안 선택)
- **Quiz Timer, Explanation Text**: 사용하지 않음
- UIManager에서 이 필드들은 Size 0 또는 비어있어야 합니다

**Quiz Panel 연결 확인:**
- [ ] Question Text 연결됨 (퀴즈 질문)
- [ ] Quiz Panel 초기 상태: 비활성화 (회색 체크 해제)

---

#### 단계 5: Result Panel Elements 연결 (게임 종료 화면)

**Result Panel**을 펼쳐서 게임 결과 화면 UI를 연결합니다.

**5-1. Result Score Text (최종 점수)**
   - **위치**: `Canvas → Result Panel → ResultScoreText`
   - **연결**: UIManager의 **Result Score Text** 슬롯에 드래그
   - **역할**: 게임 종료 시 최종 점수 표시 (예: "점수: 10")

**5-2. Result Distance Text (최종 거리)**
   - **위치**: `Canvas → Result Panel → ResultDistanceText`
   - **연결**: UIManager의 **Result Distance Text** 슬롯에 드래그
   - **역할**: 게임 종료 시 총 이동 거리 표시 (예: "거리: 532m")

**5-3. Result Time Text (플레이 시간)**
   - **위치**: `Canvas → Result Panel → ResultTimeText`
   - **연결**: UIManager의 **Result Time Text** 슬롯에 드래그
   - **역할**: 게임 종료 시 플레이 시간 표시 (예: "시간: 02:15")

**5-4. Result Correct Text (정답 개수)**
   - **위치**: `Canvas → Result Panel → ResultCorrectText`
   - **연결**: UIManager의 **Result Correct Text** 슬롯에 드래그
   - **역할**: 맞춘 퀴즈 개수 표시 (예: "정답: 8")
   - **색상**: 초록색 (Correct Color)

**5-5. Result Wrong Text (오답 개수)**
   - **위치**: `Canvas → Result Panel → ResultWrongText`
   - **연결**: UIManager의 **Result Wrong Text** 슬롯에 드래그
   - **역할**: 틀린 퀴즈 개수 표시 (예: "오답: 2")
   - **색상**: 빨간색 (Wrong Color)

**5-6. Restart Button (재시작 버튼)**
   - **위치**: `Canvas → Result Panel → RestartButton`
   - **연결**: UIManager의 **Restart Button** 슬롯에 드래그
   - **역할**: 버튼 클릭 시 게임 재시작
   - **텍스트**: "다시 시작"

**5-7. Quit Button (종료 버튼)**
   - **위치**: `Canvas → Result Panel → QuitButton`
   - **연결**: UIManager의 **Quit Button** 슬롯에 드래그
   - **역할**: 버튼 클릭 시 게임 종료 (애플리케이션 종료)
   - **텍스트**: "종료"

**Result Panel 연결 확인:**
- [ ] Result Score Text 연결됨
- [ ] Result Distance Text 연결됨
- [ ] Result Time Text 연결됨
- [ ] Result Correct Text 연결됨 (초록색)
- [ ] Result Wrong Text 연결됨 (빨간색)
- [ ] Restart Button 연결됨
- [ ] Quit Button 연결됨
- [ ] Result Panel 초기 상태: 비활성화 (회색 체크 해제)

---

#### 단계 6: Colors 설정 (3개)

UIManager 하단의 색상 설정:

- **Correct Color**: 초록색 `RGB(0, 255, 0)`
- **Wrong Color**: 빨간색 `RGB(255, 0, 0)`
- **Normal Color**: 흰색 `RGB(255, 255, 255)`

---

#### 단계 7: 전체 연결 확인 체크리스트 ⭐

모든 연결을 마쳤으면 다음을 확인하세요.

**UIManager 컴포넌트 위치 확인:**
- [ ] Canvas 오브젝트에 UIManager 컴포넌트가 추가되어 있음
- [ ] Managers가 아닌 **Canvas**에 있음 (중요!)

---

**📌 Panels (4개) - 각 화면 패널:**
- [ ] HUD Panel: `HUD Panel` 연결됨 (게임 중 항상 표시)
- [ ] Quiz Panel: `Quiz Panel` 연결됨 (퀴즈 질문 화면)
- [ ] Result Panel: `Result Panel` 연결됨 (게임 종료 결과 화면)
- [ ] Game Over Panel: `GameOver Panel` 연결됨 (타임오버 화면, 선택사항)

---

**🎮 HUD Elements (4개) - 게임 중 정보:**
- [ ] Score Text: `ScoreText` 연결됨 (점수)
- [ ] Distance Text: `DistanceText` 연결됨 (거리)
- [ ] **Game Timer Text**: `GameTimerText` 연결됨 ⭐ (제한시간 타이머)
- [ ] **Dash Gauge Fill Image**: `DashGauge` 연결됨 ⭐ (대쉬 게이지)

---

**❓ Quiz Panel Elements (1개) - 퀴즈 화면:**
- [ ] **Question Text**: `QuestionText` 연결됨 ⭐⭐⭐ (퀴즈 질문, 가장 중요!)

---

**📊 Result Panel Elements (7개) - 결과 화면:**
- [ ] Result Score Text: 연결됨 (최종 점수)
- [ ] Result Distance Text: 연결됨 (최종 거리)
- [ ] Result Time Text: 연결됨 (플레이 시간)
- [ ] Result Correct Text: 연결됨 (정답 개수, 초록색)
- [ ] Result Wrong Text: 연결됨 (오답 개수, 빨간색)
- [ ] Restart Button: 연결됨 (재시작 버튼)
- [ ] Quit Button: 연결됨 (종료 버튼)

---

**🎨 Colors (3개) - 색상 설정:**
- [ ] Correct Color: 초록색 `RGB(0, 255, 0)` (정답 색)
- [ ] Wrong Color: 빨간색 `RGB(255, 0, 0)` (오답 색)
- [ ] Normal Color: 흰색 `RGB(255, 255, 255)` (기본 색)

---

**🔧 다른 Manager 연결:**

**QuizManager (Managers 오브젝트에 있음):**
- [ ] Quiz Json File: `quizzes` 연결됨 ⭐⭐⭐ (퀴즈 데이터)

**SegmentManager (Managers 오브젝트에 있음):**
- [ ] 연결 항목 없음 (싱글톤 Instance만 제공)

---

**✅ Panel 초기 상태 (Hierarchy에서 확인):**
- [ ] HUD Panel: **활성화** (파란색 체크 ✅)
- [ ] Quiz Panel: **비활성화** (회색, 체크 해제)
- [ ] Result Panel: **비활성화** (회색, 체크 해제)
- [ ] GameOver Panel: **비활성화** (회색, 체크 해제)

⚠️ Quiz/Result/GameOver Panel이 활성화되어 있으면 게임 시작 시 화면을 가립니다!

---

**❗ 자주 발생하는 실수:**

1. **UIManager를 Managers에 추가함**
   → UIManager는 **Canvas**에 추가해야 합니다!

2. **Quiz Json File이 비어있음**
   → Managers/QuizManager에 `quizzes` 파일 연결 필요

3. **Question Text 미연결**
   → 퀴즈 질문이 안 보이는 가장 큰 원인!

4. **Panel이 초기에 활성화되어 있음**
   → Quiz/Result Panel은 비활성화 상태여야 함

5. **TextMeshPro 대신 Text 컴포넌트 사용**
   → UI → Text - TextMeshPro로 생성했는지 확인

---

### 12.4 한글 폰트 설정 (선택사항) ⭐

퀴즈 질문이 □□□로 깨져 보이면 한글 폰트를 설정해야 합니다.

#### 방법 1: 개별 Text에 폰트 적용

1. **한글 폰트 다운로드** (예: Noto Sans KR, 나눔고딕 등)
2. **Assets/Fonts/ 폴더에 .ttf 파일 복사**
3. **Window → TextMeshPro → Font Asset Creator**
4. **설정:**
   - Source Font File: 다운받은 폰트 선택
   - Font Size: `Auto Sizing` 체크 또는 `42`
   - Character Set: `Custom Characters`
   - Custom Character List:
     ```
     기본 ASCII 문자 + 한글
     ```
   - Unicode Range (Hex): `AC00-D7A3` (한글 전체)
5. **Generate Font Atlas 클릭**
6. **Save 클릭** → `Assets/Fonts/` 폴더에 저장 (예: `NotoSansKR SDF`)

7. **적용:**
   - `Canvas/Quiz Panel/QuestionText` 선택
   - TextMeshPro 컴포넌트의 **Font Asset**을 방금 만든 SDF 폰트로 변경
   - 필요하면 다른 텍스트에도 적용

#### 방법 2: 전역 기본 폰트 변경

1. **Window → TextMeshPro → Font Asset Creator**로 한글 폰트 생성
2. **Edit → Project Settings → TextMesh Pro → Settings**
3. **Default Font Asset** 변경
4. 모든 새로운 TextMeshPro가 자동으로 이 폰트 사용

---

## 13. 테스트

### 13.1 Scene 저장
1. **File → Save As**
2. 이름: `running`
3. 위치: `Assets/Scenes/`

---

### 13.2 Play 모드 테스트

#### ✅ 테스트 1: 기본 이동
**Play 버튼 클릭**

- **방향키 ← → ↑ ↓**: 이동 확인 (WASD 비활성화됨)
- **Ctrl**: 점프 확인 (더블점프 가능)
- **Z 키 (누르고 있기)**: 대쉬 확인
- **대쉬 게이지**: HUD 좌하단에 게이지 감소/회복 확인

**문제 발생 시:**
- Player의 CharacterController 확인
- RunnerController의 Auto Run이 **체크 해제**되어 있는지 확인

---

#### ✅ 테스트 2: 트랙 확인
**Play 모드에서 앞으로 이동**

- Unity에 배치한 트랙 위에서 정상 이동하는지 확인
- 바닥 충돌이 정상 작동하는지 확인

**주의:** 자동 트랙 생성 기능은 제거되었습니다. Unity에서 직접 트랙을 배치해야 합니다.

---

#### ✅ 테스트 3: 퀴즈 시스템 ⭐⭐⭐

**사전 준비:**

Play 모드 시작 전에 다음을 확인하세요:

1. **Player 오브젝트**: ⭐⭐⭐
   - **Rigidbody 컴포넌트 존재** (Section 4.2 참고)
   - Is Kinematic: ✅ 체크
   - Use Gravity: ❌ 체크 해제
   - Tag: `Player`
   - ⚠️ **Rigidbody가 없으면 트리거가 작동하지 않습니다!**

2. **Managers/QuizManager**:
   - Quiz Json File: `quizzes` 연결됨 ✅

3. **Canvas/UIManager**:
   - Quiz Panel: 연결됨 ✅
   - Question Text: 연결됨 ✅

4. **Console 창 열기**:
   - Window → General → Console (Ctrl+Shift+C)

---

**퀴즈 트리거 수동 배치:**

1. **Play 모드 정지**
2. **Hierarchy 우클릭 → Create Empty**
3. 이름: `TestQuizTrigger`
4. Position: `(0, 1, 30)` (플레이어 앞 30m)
5. **Add Component → Quiz Trigger**
6. **Add Component → Box Collider**
   - Is Trigger: ✅ 체크
   - Center: `(0, 2, 0)`
   - Size: `(20, 5, 2)`

---

**테스트 단계:**

**1단계: Play 모드 시작**
- Play 버튼 클릭
- Console 창 확인 → 에러 없어야 함

**2단계: 트리거 진입**
- 방향키 ↑ 눌러서 앞으로 이동 (Z=30 위치까지)
- QuizTrigger 영역에 진입

**3단계: Console 로그 확인** ⭐

다음 로그가 순서대로 나와야 합니다:

```
[QuizManager] Quiz started: 대한민국의 수도는?
[QuizDoorController] Door 0: 서울 (Correct: True)
[QuizDoorController] Door 1: 부산 (Correct: False)
[QuizDoorController] Door 2: 인천 (Correct: False)
[QuizDoorController] Assigned quiz to 3 doors
```

❌ 로그가 안 나오면:
- **Player에 Rigidbody가 있는지 확인** (가장 흔한 원인!)
- Player의 Tag가 "Player"인지 확인
- QuizTrigger의 Box Collider → Is Trigger 체크
- QuizManager의 Quiz Json File 연결 확인

---

**4단계: UI 확인** ⭐⭐⭐

퀴즈 질문이 **화면 중앙에 3초간 표시**되어야 합니다:

✅ **정상:**
- 화면 중앙에 "대한민국의 수도는?" 표시
- 반투명 검정 배경 (Quiz Panel)
- 3초 후 자동으로 사라짐
- **⚠️ 중요**: 질문이 표시되는 동안에도 **게임은 계속 진행**되며 플레이어는 이동 가능합니다

❌ **문제 1: 질문이 안 보임**
→ **Canvas/UIManager** 확인:
  - Quiz Panel: `Quiz Panel` 연결됨?
  - Question Text: `QuestionText` 연결됨?
  - QuestionText가 TextMeshProUGUI 컴포넌트를 가지고 있는지?

❌ **문제 2: 질문이 □□□로 깨짐**
→ 한글 폰트 설정:
  - Section 12.4 참고하여 한글 폰트 적용

❌ **문제 3: Quiz Panel이 계속 켜져있음**
→ Quiz Panel의 초기 상태 확인:
  - Hierarchy에서 Quiz Panel 체크 해제 (비활성화)

---

**5단계: 퀴즈 문 확인**

질문이 사라진 후 **Scene 뷰**에서 확인:

✅ **정상:**
- 플레이어 앞에 3개의 문 (QuizDoor)이 보임
- 각 문에 답안 텍스트 표시 (3D Text)
- 문 색상: 흰색 (초기 상태)

❌ **문이 안 보임:**
→ **QuizDoorController** 확인:
  - ⭐ **QuizTrigger의 자식으로 DoorController가 있는지 확인** (Managers 아님!)
  - DoorController Inspector에서 Quiz Doors 배열 (Size: 3)에 3개 문이 연결되어 있는지
  - Console에 "[QuizDoorController] Assigned quiz to 3 doors" 로그 있는지

---

**6단계: 정답 문 테스트**

올바른 답 문으로 이동 (예: "서울"):

✅ **예상 결과:**
- 문을 **통과할 수 있음**
- 문이 **초록색**으로 변경
- **+5초** 시간 증가 (HUD 타이머 확인)
- Console 로그:
  ```
  [QuizDoor] Correct! Player entered door 0: 서울
  [QuizManager] Correct answer!
  ```

---

**7단계: 오답 문 테스트**

틀린 답 문으로 이동 (예: "부산"):

✅ **예상 결과:**
- 문에 **닿으면** 즉시 반응 (Collision)
- 문이 **빨간색**으로 변경
- **-5초** 시간 감소 (HUD 타이머 확인, **한 번만 적용**)
- 문이 **벽처럼 막힘** (Collider가 Solid로 설정되어 통과 불가)
- 다른 문을 찾아야 함
- Console 로그:
  ```
  [QuizDoor] Wrong! Player collided with door 1: 부산 (-5초)
  [GameTimer] Penalty applied: -5s
  ```

**⚠️ 오답 페널티:**
- 오답 문에 닿으면 -5초가 **한 번만** 적용됩니다
- 같은 오답 문에 다시 닿아도 추가 페널티 없음
- 정답 문을 찾아야 퀴즈 완료

**⚠️ 문 타입:**
- 정답 문: Trigger (통과 가능), OnTriggerEnter로 감지
- 오답 문: Solid (막힘), OnCollisionEnter로 감지

---

**8단계: HUD 타이머 확인**

화면 상단 중앙에 타이머가 표시되어야 합니다:

✅ **정상:**
- "제한시간: 01:35" 형태로 표시 (100초부터 카운트다운)
- 정답 시 +5초
- 오답 시 -5초
- 30초 이하: 노란색
- 10초 이하: 빨간색

❌ **타이머가 안 보임:**
→ **Canvas/UIManager** 확인:
  - Game Timer Text: `GameTimerText` 연결됨?
→ **Managers/GameTimerManager** 확인:
  - 컴포넌트가 존재하는지?

---

**종합 체크리스트:**

퀴즈 시스템이 정상 작동하려면 다음이 모두 ✅여야 합니다:

- [ ] Console에 `[QuizManager] Quiz started:` 로그 출력
- [ ] Console에 `[QuizDoorController] Assigned quiz to 3 doors` 로그 출력
- [ ] 화면에 퀴즈 질문 3초간 표시 (**게임은 계속 진행, 플레이어 이동 가능**)
- [ ] 3초 후 질문 숨김, 3개 문에 답안 할당
- [ ] 정답 문: 초록색, +5초, 통과 가능 (Trigger)
- [ ] 오답 문: 빨간색, -5초 (한 번만), **막힘** (Solid)
- [ ] HUD에 타이머 표시 (카운트다운)
- [ ] 한글 깨지지 않음
- [ ] 퀴즈 중복 없음 (같은 퀴즈는 한 게임에서 한 번만)

---

#### ✅ 테스트 4: UI
- **HUD 업데이트**: 점수(정답 개수), 거리, 시간 확인
- **제한시간**: 100초부터 카운트다운
- **대쉬 게이지**: Z 키 누를 때 감소, 뗄 때 회복
- **시간 색상**: 10초 이하 빨간색, 30초 이하 노란색

---

### 13.3 자동 퀴즈 트리거 추가

세그먼트에 퀴즈 트리거를 자동으로 추가하려면:

1. **TrackSegment_01 프리팹** 편집
2. 프리팹 루트 우클릭 → Create Empty
3. 이름: `QuizTriggerSpawn`
4. Position: `(0, 1, 25)` (세그먼트 중간)
5. `QuizTrigger` 프리팹을 자식으로 드래그
6. **프리팹 저장**

---

## 14. WebGL 빌드

### 14.1 Build Settings
1. **File → Build Settings**
2. **Platform → WebGL**
3. **Switch Platform**
4. **Scenes In Build**:
   - Add Open Scenes (`running.unity`)

---

### 14.2 Player Settings
**Build Settings → Player Settings**

#### Company Settings
- **Company Name**: 본인 이름
- **Product Name**: `minji_run`

#### Resolution and Presentation
- **Default Canvas Width**: `1920`
- **Default Canvas Height**: `1080`
- **Run In Background**: 체크

#### Quality
- **Quality**: Fastest 또는 Medium
- **Pixel Light Count**: `1`
- **Shadow Distance**: `50`
- **Shadow Cascades**: No Cascades

#### Other Settings
- **Color Space**: Gamma
- **Auto Graphics API**: 체크
- **Scripting Backend**: IL2CPP
- **API Compatibility Level**: .NET Standard 2.1

---

### 14.3 Build
1. **Build Settings → Build**
2. 폴더 선택: `Builds/WebGL`
3. **빌드 시작** (10-30분 소요)

---

### 14.4 로컬 테스트
빌드 완료 후 로컬 서버 실행 (파일로는 실행 안됨):

**Python 사용:**
```bash
cd Builds/WebGL
python -m http.server 8000
# 브라우저에서 localhost:8000 접속
```

**또는 Unity Editor:**
- **Build Settings → Build And Run**

---

### 14.5 온라인 호스팅

빌드 폴더를 다음 서비스에 업로드:
- **itch.io** (권장)
- **GitHub Pages**
- **Netlify**

#### itch.io 업로드 방법:
1. itch.io 계정 생성
2. **Dashboard → Create new project**
3. **Kind of project**: HTML
4. **Upload files**: Build 폴더를 ZIP으로 압축 후 업로드
5. **This file will be played in the browser**: 체크
6. **Save & view page**

---

## 🎯 최종 체크리스트

### ✅ Scene 구조
- [ ] Managers (GameStateManager, GameTimerManager, QuizManager, SegmentManager) ⭐ QuizDoorController 없음!
- [ ] Player (**Rigidbody (Is Kinematic)**, CharacterController, RunnerController, **Fall Death Y 설정**)
- [ ] Main Camera (FollowCamera)
- [ ] Canvas (UIManager, HUD/Quiz/Result Panels)
- [ ] EventSystem
- [ ] QuizZone_1 (QuizTrigger + DoorController_1) ⭐
- [ ] QuizZone_2, 3 (DoorController만, QuizTrigger 없음) ⭐
- [ ] 각 QuizZone마다 Doors (QuizDoor 3개)

### ✅ 프리팹
- [ ] TrackSegment (최소 1개)
- [ ] Obstacles (최소 3개)

### ✅ 참조 연결
- [ ] GameStateManager → GameConfig
- [ ] SegmentManager → 연결 항목 없음
- [ ] FollowCamera → Player
- [ ] UIManager → 모든 UI 요소 (HUD, Quiz, Result Panels)
- [ ] DoorController_1 → QuizDoor 3개 + Next = DoorController_2 ⭐
- [ ] DoorController_2 → QuizDoor 3개 + Next = DoorController_3 ⭐
- [ ] DoorController_3 → QuizDoor 3개 + Next = None ⭐

### ✅ 설정
- [ ] Player Tag
- [ ] **Player Rigidbody** → Is Kinematic = true, Use Gravity = false ⭐⭐⭐
- [ ] Obstacle Tag
- [ ] Ground Layer (권장, 점프 안정성)
- [ ] RunnerController → **Fall Death Y = -10**
- [ ] Auto Run: **체크 해제**

### ✅ 테스트
- [ ] 방향키 이동 (WASD 비활성화)
- [ ] Ctrl 더블점프
- [ ] Z 대쉬 + 게이지
- [ ] Unity에 배치한 트랙에서 이동
- [ ] 퀴즈 시스템 (3초 질문 표시, **게임 계속 진행** → 3개 문에 답안 할당)
- [ ] 정답 문 통과 (+5초, 초록색)
- [ ] 오답 문 충돌 (-5초 한 번만, 빨간색, **막힘**)
- [ ] ⭐ **하이브리드 체인**: 정답 통과 → 1.5초 후 다음 퀴즈 자동 시작
- [ ] ⭐ **체인 확인**: 콘솔에 "Activating next controller: DoorController_2" 로그
- [ ] 퀴즈 중복 방지 (한 게임에서 같은 퀴즈는 한 번만)
- [ ] 100초 타이머
- [ ] UI 업데이트
- [ ] **낙사 리스폰** (Y < -10 → 자동 리스폰, 마지막 안전 위치로 복귀)

---

## 🆘 자주 발생하는 문제

### ❌ QuizTrigger가 작동하지 않음 (가장 흔한 문제!) ⭐⭐⭐
✅ **해결:**
- **Player에 Rigidbody 추가** (Section 4.2 참고)
- Rigidbody 설정:
  - **Is Kinematic**: ✅ 체크 (필수!)
  - **Use Gravity**: ❌ 체크 해제
  - **Freeze Rotation X, Z**: ✅ 체크
- Player Tag가 "Player"인지 확인
- QuizTrigger의 Box Collider → Is Trigger 체크
- Console에서 "[QuizTrigger] OnTriggerEnter called!" 로그 확인

**⚠️ 증상:**
- QuizTrigger를 통과해도 퀴즈가 시작되지 않음
- 몇 초 지연 후에 퀴즈가 시작됨
- Console에 로그가 안 나옴

**⚠️ 원인:**
- Unity 물리 엔진은 Rigidbody가 있는 오브젝트만 매 프레임 추적
- Rigidbody가 없으면 OnTriggerEnter가 즉시 호출되지 않음

---

### ❌ Player가 물리 충돌에 밀림
✅ **해결:**
- Rigidbody의 **Is Kinematic**: ✅ 체크
- Is Kinematic이 체크되어 있지 않으면 물리 엔진이 플레이어를 밀어냄
- CharacterController와 함께 사용할 때는 반드시 Kinematic 모드

---

### ❌ Player가 이중으로 떨어짐 (중력이 두 배로 적용)
✅ **해결:**
- Rigidbody의 **Use Gravity**: ❌ 체크 해제
- CharacterController가 이미 중력을 처리하므로 Rigidbody의 중력은 불필요
- Use Gravity 체크 시 중력이 두 번 적용되어 빠르게 떨어짐

---

### ❌ Player가 계속 떨어짐 (낙사)
✅ **해결:**
- Y < -10 이하로 떨어지면 자동 리스폰됩니다
- Console에서 "Player fell below Y=" 로그 확인
- RunnerController의 **Fall Death Y** 값 확인 (기본값: -10)
- Unity에 배치한 트랙이 있는지 확인

### ❌ 낙사 후 리스폰이 안됨
✅ **해결:**
- RunnerController의 **Fall Death Y** 값이 설정되었는지 확인
- Player에 CharacterController와 RunnerController가 있는지 확인
- Console에서 리스폰 로그 확인
- 마지막 안전 위치가 기록되는지 확인 (지면에 있을 때 자동 업데이트)

### ❌ 이동이 안됨
✅ **해결:**
- **방향키**로 이동 (WASD 비활성화됨)
- RunnerController 설정 확인
- CharacterController 확인
- Game State가 Running인지 확인

### ❌ 대쉬가 안됨
✅ **해결:**
- **Z 키**를 **누르고 있기** (GetKey)
- Dash Gauge가 0보다 큰지 확인
- UIManager에 Dash Gauge Fill Image 연결 확인

### ❌ 트랙이 생성되지 않음
✅ **해결:**
- SegmentManager의 Prefabs 확인
- Player Transform 연결 확인
- Prefab에 TrackSegment 스크립트 확인

### ❌ 퀴즈가 시작되지 않음
✅ **해결:**
- QuizTrigger Collider가 Trigger인지 확인
- Player Tag 확인
- GameStateManager, QuizManager 존재 확인
- ⭐ **QuizTrigger의 자식으로 DoorController 있는지 확인** (Managers 아님!)
- QuizTrigger Inspector에서 Door Controller 필드 연결 확인

### ❌ 문에 답안이 할당되지 않음
✅ **해결:**
- 씬에 QuizDoor 3개가 있는지 확인 (각 QuizZone의 Doors 아래)
- ⭐ **DoorController가 QuizTrigger의 자식인지 확인** (Managers 아님!)
- DoorController Inspector에서 Quiz Doors 배열 (Size: 3) 확인
- 각 Element에 QuizDoor 3개 수동 연결 확인
- Console에 "[QuizDoorController] Assigned quiz to 3 doors" 로그 확인

### ❌ 100초 타이머가 작동 안함
✅ **해결:**
- GameTimerManager 존재 확인
- UIManager에 Game Timer Text 연결 확인
- GameStateManager가 타이머 시작하는지 확인

### ❌ UI가 표시되지 않음
✅ **해결:**
- UIManager가 Canvas에 붙어있는지 확인
- Canvas Render Mode 확인
- EventSystem 존재 확인
- Panel 활성화 상태 확인

### ❌ WebGL 빌드 실패
✅ **해결:**
- TextMeshPro 패키지 확인
- 모든 참조 연결 확인
- Console 에러 확인

---

## 📚 다음 단계

게임이 작동하면 다음 기능 추가 가능:

1. **난이도 시스템** (정답 수에 따라 장애물/문제 어려워짐)
2. **낙사 구간** (떨어지면 체크포인트로 복귀)
3. **파워업 아이템** (무적, 속도 증가 등)
4. **더 많은 퀴즈** (JSON 파일에 추가)
5. **캐릭터 애니메이션** (Mixamo)
6. **사운드** (BGM, 효과음)
7. **랭킹 시스템** (PlayerPrefs 또는 Firebase)
8. **업적 시스템**

---

## 📝 최신 변경사항 (2025-12-30)

### 🎮 퀴즈 시스템 개선

**1. 게임 일시정지 제거**
- 퀴즈가 나와도 게임이 멈추지 않습니다
- 질문이 표시되는 동안에도 플레이어는 계속 이동 가능
- 타이머도 계속 흐름 (일시정지 없음)

**2. 퀴즈 중복 방지 강화**
- 한 게임 세션에서 같은 퀴즈는 한 번만 출제
- 모든 퀴즈를 다 풀면 더 이상 퀴즈가 나오지 않음
- 자동 리셋 기능 제거

**3. QuizDoorController 최적화**
- 불필요한 코드 제거 (Visual Settings, playerTransform 등)
- 문은 프리팹이 아닌 씬에 직접 배치하는 방식
- ⭐ **하이브리드 체인 시스템**: QuizTrigger의 자식으로 배치, Next Door Controller 필드로 체인 연결
- 정답 시 자동으로 다음 QuizDoorController 활성화 (1.5초 후)

**4. 문 시스템 개선**
- 정답 문: Trigger (통과 가능), 초록색 강조
- 오답 문: Solid (막힘), 빨간색 강조, -5초 페널티는 한 번만
- QuizDoorController가 씬의 QuizDoor를 자동으로 찾아 할당 (GetComponentsInChildren)

---

**모든 설정이 완료되었습니다!** 🎉

질문이 있으면 Console 창의 에러 메시지를 확인하세요.
