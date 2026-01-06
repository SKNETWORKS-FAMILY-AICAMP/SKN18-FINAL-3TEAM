# 🎮 Unity 계층 구조 (Hierarchy)

## 전체 계층 구조

```
Scene
├─ Directional Light
├─ Player ⭐
│   ├─ CharacterController
│   ├─ RunnerController
│   └─ Rigidbody (Kinematic)
│
├─ Main Camera ⭐
│   └─ Camera
│
├─ Managers ⭐
│   ├─ GameStateManager
│   ├─ QuizManager
│   └─ GameTimerManager
│
├─ Canvas ⭐
│   ├─ UIManager
│   ├─ EventSystem
│   ├─ HUD Panel
│   │   ├─ ScoreText
│   │   ├─ DistanceText
│   │   ├─ GameTimerText ⭐
│   │   └─ DashGauge
│   │       ├─ Background
│   │       └─ Fill
│   ├─ Quiz Panel
│   │   └─ QuestionText
│   ├─ Game Over Panel
│   │   ├─ TitleText
│   │   ├─ ScoreText
│   │   └─ RestartButton
│   └─ Game Clear Panel
│       ├─ TitleText
│       ├─ ScoreText
│       └─ RestartButton
│
├─ LaneObstacleSpawner ⭐ (자동 생성기)
│   └─ LaneObstacleSpawner
│
├─ TrackSegment_1 ⭐
│   ├─ TrackSegment
│   ├─ Ground (Plane)
│   │   ├─ MeshRenderer
│   │   └─ MeshCollider (Layer: Ground)
│   ├─ ObstacleRoot (빈 오브젝트)
│   │   ├─ Obstacle_1 (수동 배치)
│   │   ├─ Obstacle_2 (수동 배치)
│   │   └─ Obstacle_3 (수동 배치)
│   └─ QuizZone (Z=40)
│       ├─ QuizTrigger (Z=40)
│       │   ├─ BoxCollider (Is Trigger: ✓)
│       │   ├─ QuizTrigger Script
│       │   └─ DoorController_1 ⭐ (자식!)
│       │       └─ QuizDoorController
│       └─ Doors (Z=45)
│           ├─ QuizDoor_Left (X=-3)
│           │   ├─ QuizDoor
│           │   ├─ BoxCollider
│           │   ├─ Left_Pillar
│           │   ├─ Right_Pillar
│           │   ├─ Top_Bar
│           │   ├─ Portal (Quad)
│           │   └─ ChoiceText (TextMeshPro)
│           ├─ QuizDoor_Center (X=0)
│           │   ├─ QuizDoor
│           │   ├─ BoxCollider
│           │   ├─ Left_Pillar
│           │   ├─ Right_Pillar
│           │   ├─ Top_Bar
│           │   ├─ Portal (Quad)
│           │   └─ ChoiceText (TextMeshPro)
│           └─ QuizDoor_Right (X=3)
│               ├─ QuizDoor
│               ├─ BoxCollider
│               ├─ Left_Pillar
│               ├─ Right_Pillar
│               ├─ Top_Bar
│               ├─ Portal (Quad)
│               └─ ChoiceText (TextMeshPro)
│
├─ TrackSegment_2
│   ├─ TrackSegment
│   ├─ Ground (Plane)
│   ├─ ObstacleRoot
│   └─ QuizZone
│       ├─ QuizTrigger
│       │   └─ DoorController_2 ⭐ (체인)
│       └─ Doors
│           ├─ QuizDoor_Left
│           ├─ QuizDoor_Center
│           └─ QuizDoor_Right
│
└─ TrackSegment_3
    ├─ TrackSegment
    ├─ Ground (Plane)
    ├─ ObstacleRoot
    └─ QuizZone
        ├─ QuizTrigger
        │   └─ DoorController_3
        └─ Doors
            ├─ QuizDoor_Left
            ├─ QuizDoor_Center
            └─ QuizDoor_Right
```

---

## 상세 설명

### 1. Player (플레이어)
```
Player
├─ Tag: Player
├─ Position: (0, 1, 0)
├─ CharacterController
│   ├─ Height: 2
│   ├─ Radius: 0.3
│   └─ Center: (0, 1, 0)
├─ RunnerController
│   ├─ Move Speed: 5
│   ├─ Dash Speed: 10
│   └─ Fall Death Y: -10
└─ Rigidbody
    ├─ Is Kinematic: ✓
    └─ Use Gravity: ✗
```

---

### 2. Main Camera (카메라)
```
Main Camera
├─ Position: (0, 5, -8)
├─ Rotation: (30, 0, 0)
└─ Camera
    ├─ Field of View: 60
    ├─ Near: 0.3
    └─ Far: 100
```

---

### 3. Managers (매니저)
```
Managers (빈 GameObject)
├─ GameStateManager
│   └─ Game Config 설정
├─ QuizManager
│   ├─ Quiz File Name: "quiz_data"
│   └─ Quiz Time Limit: 30
└─ GameTimerManager
    ├─ Start Time: 100 ⭐
    ├─ Bonus Time: 5
    └─ Penalty Time: 5
```

---

### 4. Canvas (UI)
```
Canvas
├─ Render Mode: Screen Space - Overlay
├─ UIManager ⭐ (Canvas에 붙음)
├─ EventSystem
│
├─ HUD Panel (투명)
│   ├─ ScoreText (왼쪽 상단)
│   ├─ DistanceText (왼쪽 상단)
│   ├─ GameTimerText (중앙 상단) ⭐
│   └─ DashGauge (중앙 하단)
│       ├─ Background (Image)
│       └─ Fill (Image)
│
├─ Quiz Panel (중앙 상단)
│   └─ QuestionText (TextMeshPro)
│
├─ Game Over Panel
│   ├─ TitleText
│   ├─ ScoreText
│   └─ RestartButton
│
└─ Game Clear Panel
    ├─ TitleText
    ├─ ScoreText
    └─ RestartButton
```

---

### 5. LaneObstacleSpawner (자동 생성기)
```
LaneObstacleSpawner
├─ Position: (0, 0, 0)
└─ LaneObstacleSpawner
    ├─ Auto Spawn: ✓
    ├─ Spawn Interval: 2.5
    ├─ Spawn Distance: 50
    ├─ Obstacle Prefab: Obstacle_Box
    ├─ Rush Speed: 15
    ├─ Lane Width: 3 ⭐
    └─ Spawn Patterns: 6개
```

---

### 6. TrackSegment (트랙)
```
TrackSegment_1
├─ Position: (0, 0, 0)
├─ TrackSegment Component
│   ├─ Segment Length: 50
│   └─ Obstacle Root: ObstacleRoot
│
├─ Ground
│   ├─ Type: Plane
│   ├─ Scale: (1.5, 1, 5) → 15m x 50m
│   ├─ Layer: Ground
│   └─ MeshCollider
│
├─ ObstacleRoot (빈 GameObject)
│   └─ (수동 배치 장애물들)
│
└─ QuizZone
    ├─ QuizTrigger
    │   ├─ Position: (0, 0, 40)
    │   ├─ BoxCollider
    │   │   ├─ Is Trigger: ✓
    │   │   ├─ Center: (0, 2.5, 0)
    │   │   └─ Size: (15, 5, 5)
    │   ├─ QuizTrigger Script
    │   │   └─ Door Controller: DoorController_1
    │   └─ DoorController_1 (자식 오브젝트!)
    │       ├─ Quiz Doors: Size(3)
    │       │   ├─ Element 0: QuizDoor_Left
    │       │   ├─ Element 1: QuizDoor_Center
    │       │   └─ Element 2: QuizDoor_Right
    │       ├─ Next Door Controller: DoorController_2
    │       └─ Next Quiz Delay: 1.5
    │
    └─ Doors
        ├─ QuizDoor_Left
        │   ├─ Position: (-3, 0, 45)
        │   ├─ QuizDoor Script
        │   ├─ BoxCollider
        │   │   ├─ Center: (0, 1.5, 0)
        │   │   └─ Size: (3, 3, 1)
        │   ├─ Left_Pillar (Cube)
        │   │   ├─ Position: (-1.5, 0, 0)
        │   │   └─ Scale: (0.5, 3, 0.5)
        │   ├─ Right_Pillar (Cube)
        │   │   ├─ Position: (1.5, 0, 0)
        │   │   └─ Scale: (0.5, 3, 0.5)
        │   ├─ Top_Bar (Cube)
        │   │   ├─ Position: (0, 3, 0)
        │   │   └─ Scale: (3.5, 0.5, 0.5)
        │   ├─ Portal (Quad) ⭐
        │   │   ├─ Position: (0, 1.5, 0)
        │   │   └─ Scale: (2.5, 2.5, 1)
        │   └─ ChoiceText (TextMeshPro)
        │       ├─ Position: (0, 3.5, 0)
        │       └─ Font Size: 1.5
        │
        ├─ QuizDoor_Center (X=0, Z=45)
        └─ QuizDoor_Right (X=3, Z=45)
```

---

## 🎯 핵심 위치 정리

### X축 (좌우)
```
왼쪽 레인/문:  X = -3
중앙 레인/문:  X = 0
오른쪽 레인/문: X = 3
```

### Z축 (앞뒤)
```
QuizTrigger:  Z = 40 (퀴즈 시작)
QuizDoor:     Z = 45 (문 위치)
Segment 끝:   Z = 50
```

### Y축 (높이)
```
Player:       Y = 1
Camera:       Y = 5
Door 높이:    Y = 0~3
```

---

## ⭐ 체인 연결 구조

```
QuizTrigger (TrackSegment_1)
└─ DoorController_1
    └─ Next Door Controller: DoorController_2

DoorController_2 (TrackSegment_2의 QuizTrigger 자식)
└─ Next Door Controller: DoorController_3

DoorController_3 (TrackSegment_3의 QuizTrigger 자식)
└─ Next Door Controller: null (마지막)
```

**작동 방식:**
1. Player가 QuizTrigger 통과 → DoorController_1 활성화
2. 정답 문 통과 → 1.5초 후 DoorController_2 자동 활성화
3. 정답 문 통과 → 1.5초 후 DoorController_3 자동 활성화
4. 마지막 정답 문 통과 → 게임 클리어

---

## 📦 Prefab 구조

### Obstacle_Box (프리팹)
```
Obstacle_Box
├─ Tag: Obstacle
├─ Position: (0, 0.75, 0)
├─ Scale: (1.5, 1.5, 1.5)
├─ BoxCollider (Is Trigger: ✓)
└─ ObstacleController
    ├─ Fly Mode: LaneRush
    ├─ Lane Width: 3
    └─ Rush Speed: 15
```

### TrackSegment (프리팹)
- 위의 TrackSegment 구조와 동일
- Prefabs 폴더에 저장
- 여러 세그먼트 배치 시 Prefab에서 드래그

---

## 🔧 Inspector 연결 확인

### UIManager (Canvas에)
```
HUD References:
├─ Score Text: HUD Panel/ScoreText
├─ Distance Text: HUD Panel/DistanceText
├─ Game Timer Text: HUD Panel/GameTimerText ⭐
├─ Dash Gauge Fill Image: HUD Panel/DashGauge/Fill
└─ HUD Panel: HUD Panel

Quiz References:
├─ Quiz Panel: Quiz Panel
└─ Question Text: Quiz Panel/QuestionText

Panel References:
├─ Game Over Panel: Game Over Panel
└─ Game Clear Panel: Game Clear Panel
```

### QuizTrigger
```
Door Controller: DoorController_1 (자식 오브젝트)
```

### DoorController_1
```
Quiz Doors: Size(3)
├─ Element 0: Doors/QuizDoor_Left
├─ Element 1: Doors/QuizDoor_Center
└─ Element 2: Doors/QuizDoor_Right

Next Door Controller: DoorController_2
Next Quiz Delay: 1.5
```

### LaneObstacleSpawner
```
Obstacle Prefab: Prefabs/Obstacles/Obstacle_Box
```

---

## 📊 최종 체크리스트

- [ ] Player (Tag: Player, Rigidbody Kinematic)
- [ ] Main Camera (Position: 0, 5, -8)
- [ ] Managers (3개 매니저)
- [ ] Canvas (UIManager 연결)
- [ ] LaneObstacleSpawner (Prefab 연결)
- [ ] TrackSegment (최소 1개)
- [ ] QuizTrigger → DoorController (자식 관계)
- [ ] DoorController → Quiz Doors (3개 연결)
- [ ] Next Door Controller (체인 연결)

---

**이 구조대로 설정하면 모든 시스템이 작동합니다!** 🎉
