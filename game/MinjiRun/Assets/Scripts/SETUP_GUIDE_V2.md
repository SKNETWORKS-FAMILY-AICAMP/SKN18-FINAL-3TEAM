# 🎮 Unity 퀴즈 러닝 게임 완전 설정 가이드 v2.0

> **템플런 스타일 레인 시스템 + 퀴즈 + 날아가는 장애물**

---

## 📋 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [빠른 시작 (핵심만)](#2-빠른-시작-핵심만)
3. [기본 설정](#3-기본-설정)
4. [플레이어 설정](#4-플레이어-설정)
5. [카메라 설정](#5-카메라-설정)
6. [트랙 시스템](#6-트랙-시스템)
7. [레인 시스템](#7-레인-시스템)
8. [장애물 시스템](#8-장애물-시스템)
9. [퀴즈 시스템](#9-퀴즈-시스템)
10. [UI 시스템](#10-ui-시스템)
11. [매니저 설정](#11-매니저-설정)
12. [테스트 및 디버깅](#12-테스트-및-디버깅)

---

## 1. 프로젝트 개요

### 🎯 게임 특징
- **템플런 스타일** 3레인 러닝 게임
- **퀴즈 통합** 정답 문 통과 시 다음 퀴즈 자동 시작
- **다양한 장애물** 7가지 날아가기 모드
- **레인 자동 스포너** 주기적으로 1~3개 레인에 장애물 생성
- **100초 타이머** 정답 +5초, 오답 -5초

### 📐 핵심 크기 설정 (모두 동일!)
```
캐릭터: Height 2m, Radius 0.3m
트랙: Width 15m, Length 50m
레인: Width 3m (왼쪽 X=-3, 중앙 X=0, 오른쪽 X=3)
문: 높이 3m, 간격 3m
카메라: Position (0, 5, -8), Rotation (30, 0, 0)
```

---

## 2. 빠른 시작 (핵심만)

### ⚡ 5분 설정 체크리스트

#### Step 1: 씬 기본 구조
```
Managers (빈 GameObject)
├─ GameStateManager
├─ QuizManager
├─ GameTimerManager
└─ UIManager (Canvas에 붙음)

Player
├─ CharacterController (Height: 2, Radius: 0.3)
├─ RunnerController
└─ Rigidbody (Kinematic: ✓, Use Gravity: ✗)

Main Camera
├─ Position: (0, 5, -8)
└─ Rotation: (30, 0, 0)

Canvas (UI)
├─ HUD Panel
└─ Quiz Panel

LaneObstacleSpawner
├─ Spawn Interval: 2.5
├─ Obstacle Prefab: Obstacle_Box
└─ Lane Width: 3
```

#### Step 2: 필수 태그
```
Tags:
- Player
- Obstacle
```

#### Step 3: 필수 레이어
```
Layers:
- Ground (트랙)
- Player
```

---

## 3. 기본 설정

### 3.1 프로젝트 설정

1. **Unity 버전**: 2021.3 LTS 이상
2. **TextMeshPro 설치**:
   - Window → Package Manager
   - TextMeshPro 검색 → Import

### 3.2 폴더 구조
```
Assets/
├─ Scripts/
│   ├─ Managers/
│   ├─ Player/
│   ├─ Quiz/
│   ├─ Track/
│   └─ Obstacle/
├─ Prefabs/
│   ├─ Obstacles/
│   ├─ Track/
│   └─ Quiz/
├─ Materials/
└─ Resources/
    └─ quiz_data.json
```

---

## 4. 플레이어 설정

### 4.1 Player GameObject 생성

1. **Hierarchy → Create → 3D Object → Capsule**
2. 이름: `Player`
3. Tag: `Player`

### 4.2 Transform
```
Position: (0, 1, 0)
Rotation: (0, 0, 0)
Scale: (1, 1, 1)
```

### 4.3 CharacterController
```
Add Component → Character Controller

Center: (0, 1, 0)
Radius: 0.3
Height: 2
Slope Limit: 45
Step Offset: 0.3
Skin Width: 0.08
```

### 4.4 Rigidbody (필수!)
```
Add Component → Rigidbody

Mass: 1
Drag: 0
Angular Drag: 0.05
Use Gravity: ✗ (체크 해제!)
Is Kinematic: ✓ (체크!)
Interpolate: None
Collision Detection: Discrete

Constraints:
- Freeze Rotation X: ✓
- Freeze Rotation Z: ✓
```

### 4.5 RunnerController
```
Add Component → Runner Controller

Movement:
├─ Move Speed: 5
├─ Jump Force: 8
├─ Gravity: 20
└─ Rotation Speed: 10

Dash:
├─ Dash Speed: 10
├─ Max Dash Gauge: 100
├─ Dash Gauge Depletion Rate: 50
├─ Dash Gauge Recovery Rate: 20
└─ Dash Cooldown Time: 1

Ground Check:
├─ Ground Check Distance: 0.3
├─ Ground Layer: Ground
└─ Fall Death Y: -10

Knockback:
├─ Knockback Force: 5
├─ Knockback Duration: 0.3
└─ Knockback Upward Force: 2
```

---

## 5. 카메라 설정

### 5.1 Main Camera
```
Transform:
├─ Position: (0, 5, -8)
├─ Rotation: (30, 0, 0)
└─ Scale: (1, 1, 1)

Camera:
├─ Field of View: 60
├─ Clipping Planes:
│   ├─ Near: 0.3
│   └─ Far: 100
└─ Clear Flags: Skybox
```

### 5.2 카메라 추적 (선택사항)
```csharp
// CameraFollow.cs (선택사항)
public Transform target;  // Player 드래그
public Vector3 offset = new Vector3(0, 5, -8);
public float smoothSpeed = 5f;
```

---

## 6. 트랙 시스템

### 6.1 TrackSegment 프리팹 생성

1. **Hierarchy → Create Empty**
2. 이름: `TrackSegment_1`

#### Ground (바닥)
```
Hierarchy → 3D Object → Plane

Transform:
├─ Position: (0, 0, 0)
├─ Rotation: (0, 0, 0)
└─ Scale: (1.5, 1, 5)  // 15m x 50m

MeshRenderer:
└─ Material: Ground Material

MeshCollider:
├─ Convex: ✗
└─ Layer: Ground
```

#### TrackSegment Component
```
Add Component → Track Segment

Segment Length: 50
Start Point: 자동 설정됨
End Point: 자동 설정됨
Obstacle Root: ObstacleRoot (드래그)
```

### 6.2 계층 구조
```
TrackSegment_1
├─ Ground (Plane)
├─ ObstacleRoot (빈 오브젝트)
│   └─ (수동 배치 장애물들)
├─ QuizZone
│   ├─ QuizTrigger
│   │   └─ DoorController
│   └─ Doors
│       ├─ QuizDoor_Left
│       ├─ QuizDoor_Center
│       └─ QuizDoor_Right
```

---

## 7. 레인 시스템

### 7.1 레인 구조
```
트랙 너비: 15m
레인 개수: 3개
레인 간격: 3m

레인 0 (왼쪽):  X = -3
레인 1 (중앙):  X = 0
레인 2 (오른쪽): X = 3
```

### 7.2 LaneObstacleSpawner 설정

1. **Hierarchy → Create Empty**
2. 이름: `LaneObstacleSpawner`
3. **Add Component → Lane Obstacle Spawner**

```
Spawner Settings:
├─ Auto Spawn: ✓
├─ Spawn Interval: 2.5 (초)
├─ Spawn Distance: 50 (m)
└─ Spawn Height: 1 (m)

Obstacle Prefab:
├─ Obstacle Prefab: Obstacle_Box (드래그)
└─ Obstacle Rush Speed: 15

Lane Settings:
├─ Lane Width: 3 ⭐ 중요!
├─ Min Lanes: 1
└─ Max Lanes: 2

Pattern Settings:
├─ Use Patterns: ✓
└─ Spawn Patterns: Size(6)
```

### 7.3 Spawn Patterns 설정
```
Element 0: Single_Left
├─ Pattern Name: "Single_Left"
├─ Lanes: Size(1) → [0]
└─ Probability: 0.2

Element 1: Single_Center
├─ Pattern Name: "Single_Center"
├─ Lanes: Size(1) → [1]
└─ Probability: 0.2

Element 2: Single_Right
├─ Pattern Name: "Single_Right"
├─ Lanes: Size(1) → [2]
└─ Probability: 0.2

Element 3: Double_LeftCenter
├─ Pattern Name: "Double_LeftCenter"
├─ Lanes: Size(2) → [0, 1]
└─ Probability: 0.15

Element 4: Double_CenterRight
├─ Pattern Name: "Double_CenterRight"
├─ Lanes: Size(2) → [1, 2]
└─ Probability: 0.15

Element 5: Double_LeftRight
├─ Pattern Name: "Double_LeftRight"
├─ Lanes: Size(2) → [0, 2]
└─ Probability: 0.1
```

---

## 8. 장애물 시스템

### 8.1 Obstacle 프리팹 생성

1. **Hierarchy → 3D Object → Cube**
2. 이름: `Obstacle_Box`
3. Tag: `Obstacle`

```
Transform:
├─ Position: (0, 0.75, 0)
└─ Scale: (1.5, 1.5, 1.5)

BoxCollider:
├─ Is Trigger: ✓
├─ Center: (0, 0, 0)
└─ Size: (1, 1, 1)
```

### 8.2 ObstacleController 설정

**Add Component → Obstacle Controller**

#### 기본 회전 장애물
```
Rotation Animation:
├─ Rotate: ✓
└─ Rotation Speed: (0, 50, 0)

Flying Settings:
└─ Fly Mode: None
```

#### 레인 돌진 장애물 (템플런)
```
Flying Settings:
├─ Fly Mode: LaneRush
├─ Destroy On Distance: ✓
└─ Max Distance: 100

Lane Rush Settings:
├─ Lane Index: 1 (0=왼쪽, 1=중앙, 2=오른쪽)
├─ Lane Width: 3 ⭐
└─ Rush Speed: 15
```

#### 플레이어 추적 장애물
```
Flying Settings:
├─ Fly Mode: TargetPlayer
├─ Fly Speed: 8
├─ Activation Delay: 0.5
├─ Destroy On Distance: ✓
└─ Max Distance: 100
```

#### 부유 장애물
```
Flying Settings:
├─ Fly Mode: Float
├─ Fly Direction: (0, 0, 1)
├─ Fly Speed: 5
├─ Float Amplitude: 2
└─ Float Frequency: 1
```

#### 파도 장애물
```
Flying Settings:
├─ Fly Mode: Wave
├─ Fly Direction: (0, 0, 1)
├─ Fly Speed: 6
├─ Wave Amplitude: 3
└─ Wave Frequency: 2
```

### 8.3 Fly Mode 전체 목록

| Mode | 설명 | 용도 |
|------|------|------|
| None | 날아가지 않음 | 회전/왕복만 |
| Projectile | 직선 발사 | 화살, 총알 |
| TargetPlayer | 플레이어 추적 | 유도 미사일 |
| LaneRush | 레인 돌진 | 템플런 스타일 ⭐ |
| Float | 부유 이동 | 새, 드론 |
| Wave | 파도 이동 | 뱀, 물결 |
| Circle | 원형 이동 | 회전 공격 |

---

## 9. 퀴즈 시스템

### 9.1 quiz_data.json 준비

**Assets/Resources/quiz_data.json**
```json
{
  "quizzes": [
    {
      "question": "Unity에서 게임 오브젝트를 비활성화하는 함수는?",
      "correctAnswer": "SetActive(false)",
      "wrongAnswers": ["Destroy()", "Hide()"]
    },
    {
      "question": "C#에서 배열의 길이를 구하는 속성은?",
      "correctAnswer": "Length",
      "wrongAnswers": ["Size", "Count"]
    }
  ]
}
```

### 9.2 QuizDoor 프리팹 생성

#### 문 구조
```
QuizDoor
├─ Left_Pillar (Cube)
│   └─ Scale: (0.5, 3, 0.5)
├─ Right_Pillar (Cube)
│   └─ Scale: (0.5, 3, 0.5)
├─ Top_Bar (Cube)
│   └─ Scale: (3.5, 0.5, 0.5)
├─ Portal (Quad) ⭐ 통과 영역
│   └─ Scale: (2.5, 2.5, 1)
└─ ChoiceText (TextMeshPro)
    └─ Font Size: 1.5
```

#### QuizDoor Component
```
Add Component → Quiz Door

Choice Index: 0
Choice Text: ""
Is Correct Answer: ✗

UI References:
└─ Choice Label: ChoiceText (드래그)

Visual Settings:
├─ Normal Color: White
├─ Correct Color: Green
└─ Wrong Color: Red

Portal Effect:
└─ Portal Effect: Portal (드래그)
```

#### BoxCollider 설정
```
BoxCollider:
├─ Is Trigger: 자동 설정됨 (정답: ✓, 오답: ✗)
├─ Center: (0, 1.5, 0)
└─ Size: (3, 3, 1)
```

### 9.3 QuizZone 배치

#### 계층 구조
```
QuizZone (Z=40)
├─ QuizTrigger
│   ├─ BoxCollider (Is Trigger: ✓, Size: (15, 5, 5))
│   ├─ QuizTrigger Script
│   │   └─ Door Controller: DoorController (자식)
│   └─ DoorController
│       ├─ Quiz Doors: Size(3)
│       │   ├─ Element 0: QuizDoor_Left
│       │   ├─ Element 1: QuizDoor_Center
│       │   └─ Element 2: QuizDoor_Right
│       ├─ Next Door Controller: DoorController_2
│       └─ Next Quiz Delay: 1.5
└─ Doors
    ├─ QuizDoor_Left (X=-3, Z=45)
    ├─ QuizDoor_Center (X=0, Z=45)
    └─ QuizDoor_Right (X=3, Z=45)
```

### 9.4 문 위치
```
왼쪽 문:  Position: (-3, 0, 45)
중앙 문:  Position: (0, 0, 45)
오른쪽 문: Position: (3, 0, 45)
```

### 9.5 체인 시스템

**첫 번째 세그먼트:**
```
QuizTrigger (Z=40)
└─ DoorController
    └─ Next Door Controller: DoorController_2
```

**두 번째 세그먼트:**
```
DoorController_2 (QuizTrigger의 자식)
└─ Next Door Controller: DoorController_3
```

**작동 방식:**
1. QuizTrigger 통과 → 첫 퀴즈 시작
2. 정답 문 통과 → 1.5초 후 DoorController_2 자동 활성화
3. 다음 정답 문 통과 → 1.5초 후 DoorController_3 활성화

---

## 10. UI 시스템

### 10.1 Canvas 설정
```
Canvas:
├─ Render Mode: Screen Space - Overlay
├─ Canvas Scaler:
│   ├─ UI Scale Mode: Scale With Screen Size
│   ├─ Reference Resolution: (1920, 1080)
│   └─ Match: 0.5
└─ Graphic Raycaster: ✓
```

### 10.2 HUD Panel
```
HUD Panel (투명)
├─ ScoreText (왼쪽 상단)
│   ├─ Position: (150, -30)
│   ├─ Text: "점수: 0"
│   └─ Font Size: 24
├─ DistanceText
│   ├─ Position: (150, -70)
│   └─ Text: "거리: 0m"
├─ GameTimerText ⭐
│   ├─ Position: (960, -30) - 중앙 상단
│   ├─ Text: "100"
│   ├─ Font Size: 36
│   └─ Color: Yellow
└─ DashGauge
    ├─ Position: (960, -950) - 중앙 하단
    ├─ Background (회색)
    └─ Fill (흰색)
```

### 10.3 Quiz Panel
```
Quiz Panel (중앙 상단)
├─ Background (반투명 검정)
└─ QuestionText
    ├─ Position: (0, 400)
    ├─ Size: (1600, 100)
    ├─ Font Size: 32
    ├─ Color: White
    └─ Alignment: Center
```

### 10.4 UIManager 연결
```
UIManager (Canvas에 붙음)

HUD References:
├─ Score Text: ScoreText
├─ Distance Text: DistanceText
├─ Game Timer Text: GameTimerText ⭐
├─ Dash Gauge Fill Image: DashGauge/Fill
└─ HUD Panel: HUD Panel

Quiz References:
├─ Quiz Panel: Quiz Panel
└─ Question Text: QuestionText

Panel References:
├─ Game Over Panel: GameOverPanel
└─ Game Clear Panel: GameClearPanel
```

---

## 11. 매니저 설정

### 11.1 Managers GameObject
```
Hierarchy → Create Empty
이름: Managers
Position: (0, 0, 0)
```

### 11.2 GameStateManager
```
Add Component → Game State Manager

Game Config:
├─ Move Speed: 5
├─ Jump Force: 8
├─ Gravity: 20
└─ Rotation Speed: 10
```

### 11.3 QuizManager
```
Add Component → Quiz Manager

Quiz Settings:
├─ Quiz File Name: "quiz_data"
└─ Quiz Time Limit: 30
```

### 11.4 GameTimerManager
```
Add Component → Game Timer Manager

Timer Settings:
├─ Start Time: 100 ⭐
├─ Bonus Time: 5
└─ Penalty Time: 5
```

---

## 12. 테스트 및 디버깅

### 12.1 필수 체크리스트

#### 플레이어
- [ ] CharacterController Height: 2
- [ ] Rigidbody Kinematic: ✓
- [ ] Rigidbody Use Gravity: ✗
- [ ] Tag: Player
- [ ] RunnerController 연결됨

#### 카메라
- [ ] Position: (0, 5, -8)
- [ ] Rotation: (30, 0, 0)
- [ ] 3개 레인 모두 보임

#### 레인 시스템
- [ ] Lane Width: 3 (모든 곳 동일!)
- [ ] LaneObstacleSpawner 설정됨
- [ ] Obstacle Prefab 연결됨
- [ ] Spawn Patterns 6개 설정됨

#### 퀴즈 시스템
- [ ] quiz_data.json in Resources/
- [ ] QuizTrigger → DoorController (자식)
- [ ] DoorController → Quiz Doors (3개 연결)
- [ ] Next Door Controller 체인 연결
- [ ] 문 위치: X=-3, 0, 3

#### UI
- [ ] Canvas → UIManager
- [ ] GameTimerText 연결 ⭐
- [ ] Quiz Panel 연결
- [ ] HUD Panel 연결

#### 매니저
- [ ] GameStateManager
- [ ] QuizManager
- [ ] GameTimerManager
- [ ] UIManager (Canvas에)

### 12.2 테스트 순서

1. **플레이어 이동 테스트**
   - 방향키: 좌우 이동
   - Space: 점프
   - Z키 (누르고 있기): 대쉬

2. **레인 테스트**
   - 플레이어가 레인 0, 1, 2를 정확히 이동하는지
   - 장애물이 각 레인 중앙에 생성되는지

3. **장애물 테스트**
   - 2.5초마다 자동 생성되는지
   - 충돌 시 Knockback 작동하는지
   - 뒤로 지나가면 자동 제거되는지

4. **퀴즈 테스트**
   - QuizTrigger 통과 → 퀴즈 시작
   - 정답 문 통과 → 다음 퀴즈 1.5초 후 시작
   - 오답 문 충돌 → -5초 페널티
   - 3개 문이 레인에 정확히 배치되는지

5. **타이머 테스트**
   - 게임 시작: 100초
   - 정답: +5초
   - 오답: -5초
   - 0초 도달: Game Over

### 12.3 자주 발생하는 문제

#### ❌ QuizTrigger가 작동 안함
✅ **해결:**
- Player에 Rigidbody 있는지 확인
- Rigidbody Kinematic: ✓
- QuizTrigger Is Trigger: ✓

#### ❌ 장애물이 레인 중앙에 안 옴
✅ **해결:**
- LaneObstacleSpawner Lane Width: 3
- ObstacleController Lane Width: 3
- 모든 Lane Width 값이 동일한지 확인!

#### ❌ 두 번째 퀴즈가 안 나옴
✅ **해결:**
- DoorController Next Door Controller 연결 확인
- Next Door Controller가 QuizTrigger의 자식인지 확인

#### ❌ 문에 텍스트가 안 보임
✅ **해결:**
- QuizDoor Choice Label 연결 확인
- TextMeshPro Font Asset 있는지 확인

#### ❌ 타이머가 작동 안함
✅ **해결:**
- GameTimerManager 존재 확인
- UIManager Game Timer Text 연결 확인
- GameStateManager가 타이머 시작하는지 확인

---

## 📊 권장 난이도 설정

### 🟢 쉬움
```
LaneObstacleSpawner:
- Spawn Interval: 3.5
- Rush Speed: 10
- Min Lanes: 1
- Max Lanes: 1

Player:
- Move Speed: 6
- Dash Speed: 12

Timer:
- Start Time: 120
```

### 🟡 보통 (기본)
```
LaneObstacleSpawner:
- Spawn Interval: 2.5
- Rush Speed: 15
- Min Lanes: 1
- Max Lanes: 2

Player:
- Move Speed: 5
- Dash Speed: 10

Timer:
- Start Time: 100
```

### 🔴 어려움
```
LaneObstacleSpawner:
- Spawn Interval: 2.0
- Rush Speed: 20
- Min Lanes: 2
- Max Lanes: 2

Player:
- Move Speed: 5
- Dash Speed: 10

Timer:
- Start Time: 80
```

### 🟣 매우 어려움
```
LaneObstacleSpawner:
- Spawn Interval: 1.5
- Rush Speed: 25
- Min Lanes: 2
- Max Lanes: 3
- Lane Width: 2.5 (좁은 레인!)

Player:
- Move Speed: 5
- Dash Speed: 10

Timer:
- Start Time: 60
```

---

## 🎯 핵심 요약

### ✅ 반드시 확인할 3가지

1. **Lane Width = 3** (모든 곳에 동일!)
   - LaneObstacleSpawner
   - ObstacleController (LaneRush)
   - 문 간격

2. **Rigidbody 설정** (Player)
   - Is Kinematic: ✓
   - Use Gravity: ✗

3. **QuizDoor Controller 체인**
   - QuizTrigger → DoorController (자식)
   - DoorController → Next Door Controller

### 🎮 조작법

```
방향키: 좌우 이동
Space: 점프
Z키 (누르고 있기): 대쉬
```

### 📐 핵심 크기

```
캐릭터: 2m
트랙: 15m x 50m
레인: 3m 간격
카메라: (0, 5, -8)
```

---

**설정 완료! 게임을 시작하세요!** 🎉

더 자세한 설정값은 [RECOMMENDED_SETTINGS.md](RECOMMENDED_SETTINGS.md)를 참고하세요.
