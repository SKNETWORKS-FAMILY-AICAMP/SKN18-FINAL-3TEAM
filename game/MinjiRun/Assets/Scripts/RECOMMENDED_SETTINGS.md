# 🎮 추천 게임 설정 가이드

모든 시스템(레인, 퀴즈, 장애물)이 조화롭게 작동하는 최적의 설정값입니다.

---

## 📏 1. 기본 스케일 설정

### 🏃 캐릭터 (Player)

```
Transform:
├─ Position: (0, 1, 0)
├─ Rotation: (0, 0, 0)
└─ Scale: (1, 1, 1)

CharacterController:
├─ Center: (0, 1, 0)
├─ Radius: 0.3
└─ Height: 2
```

**설명:**
- Height 2 = 일반적인 사람 키 (Unity 기본 Capsule 크기)
- Radius 0.3 = 몸통 너비
- Center Y=1 = 캡슐의 중심이 발 위 1m 위치

---

### 🛤️ 트랙 (TrackSegment)

```
Ground Plane:
├─ Scale: (15, 1, 50)
│   ├─ Width: 15m (레인 3개 + 여유 공간)
│   ├─ Depth: 1m (바닥 두께)
│   └─ Length: 50m (세그먼트 길이)

TrackSegment Component:
└─ Segment Length: 50
```

**레이아웃:**
```
[왼쪽 레인][중앙 레인][오른쪽 레인]
   (X=-3)    (X=0)     (X=3)
|----5m----|----5m----|----5m----| = 15m 총 너비
```

---

### 🚪 퀴즈 문 (QuizDoor)

```
Door Structure (각 문):
├─ Left Pillar:
│   ├─ Position: (-1.5, 0, Z)
│   └─ Scale: (0.5, 3, 0.5)
│
├─ Right Pillar:
│   ├─ Position: (1.5, 0, Z)
│   └─ Scale: (0.5, 3, 0.5)
│
├─ Top Bar:
│   ├─ Position: (0, 3, Z)
│   └─ Scale: (3.5, 0.5, 0.5)
│
├─ Portal (통과 영역):
│   ├─ Position: (0, 1.5, Z)
│   └─ Scale: (2.5, 2.5, 0.1)
│
└─ Text Label:
    ├─ Position: (0, 3.5, Z)
    └─ Font Size: 1.5

Door BoxCollider:
├─ Center: (0, 1.5, 0)
└─ Size: (3, 3, 1)
```

**3개 문 간격:**
```
왼쪽 문: X = -3 (레인 0)
중앙 문: X = 0  (레인 1)
오른쪽 문: X = 3  (레인 2)

Z 위치: 같은 위치 (예: Z=45)
```

---

### 🧱 장애물 (Obstacle)

#### 레인 장애물 (LaneRush)
```
Transform:
├─ Position: 자동 (LaneObstacleSpawner가 설정)
└─ Scale: (1.5, 1.5, 1.5)

ObstacleController:
├─ Fly Mode: LaneRush
├─ Lane Width: 3
└─ Rush Speed: 15

Collider:
├─ Is Trigger: ✓
└─ Size: (1.5, 1.5, 1.5)
```

#### 일반 장애물 (고정/회전)
```
Transform:
└─ Scale: (1, 1, 1)

ObstacleController:
├─ Rotate: ✓
├─ Rotation Speed: (0, 50, 0)
└─ Move: 옵션
```

---

## 📹 2. 카메라 설정

### Main Camera

```
Transform:
├─ Position: (0, 5, -8)
├─ Rotation: (30, 0, 0)
└─ Scale: (1, 1, 1)

Camera Component:
├─ Field of View: 60
├─ Clipping Planes:
│   ├─ Near: 0.3
│   └─ Far: 100
└─ Clear Flags: Skybox

Follow Script (있다면):
├─ Target: Player
├─ Offset: (0, 5, -8)
├─ Smooth Speed: 5
└─ Look Ahead: (0, 0, 3)
```

**설명:**
- Y=5: 플레이어 위 5m (전체 레인 보임)
- Z=-8: 플레이어 뒤 8m (앞쪽 장애물 미리 보임)
- Rotation X=30: 위에서 아래로 30도 내려다봄

---

## 🎯 3. 레인 시스템 설정

### LaneObstacleSpawner

```
Spawner Settings:
├─ Auto Spawn: ✓
├─ Spawn Interval: 2.5
├─ Spawn Distance: 50 (카메라 시야 밖)
└─ Spawn Height: 1

Obstacle Prefab:
├─ Obstacle Prefab: Obstacle_Box
└─ Obstacle Rush Speed: 15

Lane Settings:
├─ Lane Width: 3 ⭐ 중요!
├─ Min Lanes: 1
└─ Max Lanes: 2

Pattern Settings:
├─ Use Patterns: ✓
└─ Spawn Patterns: 6개 (기본)
```

---

## 🏃‍♂️ 4. 플레이어 이동 설정

### RunnerController

```
Movement Settings:
├─ Move Speed: 5
├─ Jump Force: 8
├─ Gravity: 20
└─ Rotation Speed: 10

Dash Settings:
├─ Dash Speed: 10
├─ Max Dash Gauge: 100
├─ Dash Gauge Depletion Rate: 50
├─ Dash Gauge Recovery Rate: 20
└─ Dash Cooldown Time: 1

Ground Check:
├─ Ground Check Distance: 0.3
├─ Ground Layer: Ground
└─ Fall Death Y: -10
```

---

## 🎮 5. 게임 밸런스 설정

### 난이도별 권장 설정

#### 🟢 쉬움 (초보자)
```
LaneObstacleSpawner:
├─ Spawn Interval: 3.5
├─ Rush Speed: 10
├─ Min Lanes: 1
└─ Max Lanes: 1

Player:
├─ Move Speed: 6
└─ Dash Speed: 12

Timer:
└─ Start Time: 120초
```

#### 🟡 보통
```
LaneObstacleSpawner:
├─ Spawn Interval: 2.5
├─ Rush Speed: 15
├─ Min Lanes: 1
└─ Max Lanes: 2

Player:
├─ Move Speed: 5
└─ Dash Speed: 10

Timer:
└─ Start Time: 100초
```

#### 🔴 어려움
```
LaneObstacleSpawner:
├─ Spawn Interval: 2.0
├─ Rush Speed: 20
├─ Min Lanes: 2
└─ Max Lanes: 2

Player:
├─ Move Speed: 5
└─ Dash Speed: 10

Timer:
└─ Start Time: 80초
```

#### 🟣 매우 어려움
```
LaneObstacleSpawner:
├─ Spawn Interval: 1.5
├─ Rush Speed: 25
├─ Min Lanes: 2
└─ Max Lanes: 3
├─ Lane Width: 2.5 (좁은 레인)

Player:
├─ Move Speed: 5
└─ Dash Speed: 10

Timer:
└─ Start Time: 60초
```

---

## 📐 6. 시각적 가이드라인

### 화면 비율 계산
```
카메라 FOV: 60도
카메라 높이: 5m
카메라 거리: 8m

플레이어 앞쪽 시야: ~15m
양 옆 시야: ~10m (레인 3개 전부 보임)
```

### 장애물 가시 거리
```
Spawn Distance: 50m
Rush Speed: 15m/s
도달 시간: 50 / 15 = 3.3초

플레이어가 장애물을 보고 반응할 시간: 약 3초
```

### 퀴즈 문 배치
```
각 TrackSegment:
├─ 길이: 50m
└─ 문 위치: Z=45 (끝에서 5m 전)

문 간 거리: 50m (다음 세그먼트)
```

---

## 🔧 7. 최적화 팁

### ⚡ 성능 최적화

```
LaneObstacleSpawner:
└─ Max Distance: 100 (너무 멀리 가면 제거)

Obstacle:
└─ Destroy On Distance: ✓ (화면 밖 제거)

Camera:
├─ Far Clipping: 100 (멀리 있는 것 안 그림)
└─ Occlusion Culling: ✓ (안 보이는 것 안 그림)
```

### 🎨 비주얼 팁

```
레인 마커 (선택사항):
├─ 왼쪽 레인: X=-3에 라인 그리기
├─ 중앙 레인: X=0에 라인 그리기
└─ 오른쪽 레인: X=3에 라인 그리기

바닥 텍스처:
└─ Tiling: (3, 10) - 레인 3개, 길이 반복
```

---

## ✅ 8. 체크리스트

### 설정 확인사항

- [ ] Player Height: 2m
- [ ] Track Width: 15m
- [ ] Track Length: 50m
- [ ] Lane Width: 3m ⭐ 모든 곳에 동일하게!
- [ ] Camera Y: 5m
- [ ] Camera Z: -8m
- [ ] Camera Rotation X: 30도
- [ ] Spawn Distance: 50m
- [ ] Rush Speed: 15m/s
- [ ] Spawn Interval: 2.5초
- [ ] 문 높이: 3m
- [ ] 문 간격: 3m (레인 간격과 동일)

---

## 🎯 9. 실전 테스트

### 테스트 순서

1. **레인 테스트**
   - 플레이어가 레인 0, 1, 2를 정확히 이동하는지
   - 장애물이 각 레인 중앙에 오는지

2. **카메라 테스트**
   - 3개 레인이 모두 화면에 보이는지
   - 장애물이 충분히 멀리서 보이는지 (3초 전)

3. **퀴즈 문 테스트**
   - 3개 문이 각 레인에 정확히 배치되는지
   - 문 사이로 통과 가능한지

4. **밸런스 테스트**
   - 장애물 피하기 난이도 적절한지
   - 퀴즈 풀 시간 충분한지

---

## 🚀 10. 빠른 설정 (복사해서 사용)

### Player 설정
```
Position: (0, 1, 0)
CharacterController Height: 2
CharacterController Radius: 0.3
Move Speed: 5
Dash Speed: 10
```

### Camera 설정
```
Position: (0, 5, -8)
Rotation: (30, 0, 0)
FOV: 60
```

### Track 설정
```
Ground Scale: (15, 1, 50)
Segment Length: 50
```

### LaneObstacleSpawner 설정
```
Spawn Interval: 2.5
Spawn Distance: 50
Rush Speed: 15
Lane Width: 3
Min Lanes: 1
Max Lanes: 2
```

### QuizDoor 설정
```
Door Scale: (3.5, 3, 0.5)
Door Spacing: 3m (X축)
Door Position Z: 45 (세그먼트 끝)
```

---

**이 설정값들로 시작하면 모든 시스템이 조화롭게 작동합니다!** 🎉

필요에 따라 Rush Speed, Spawn Interval 등을 조정하여 난이도를 변경할 수 있습니다.
