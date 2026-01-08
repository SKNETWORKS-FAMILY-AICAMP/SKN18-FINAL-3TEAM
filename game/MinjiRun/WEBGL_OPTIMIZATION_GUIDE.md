# Unity WebGL 최적화 가이드 - MinjiRun

## 목표
- **빌드 크기**: 50MB 이하 (압축 후)
- **로딩 시간**: 1-2분 이내
- **성능**: 데스크톱 30+ FPS

---

## 1. 프로젝트 설정

### Build Settings
```
File → Build Settings → WebGL

Player Settings:
- Publishing Settings
  ✅ Compression Format: Brotli (최고 압축률)
  ✅ Decompression Fallback: 체크
  ✅ Data Caching: 체크 (재방문 시 빠름)

- Resolution and Presentation
  ✅ Default Canvas Width: 1280
  ✅ Default Canvas Height: 720
  ✅ Run In Background: 체크 해제 (성능)

- Other Settings
  ✅ Color Space: Linear
  ✅ Auto Graphics API: WebGL2만
  ✅ Managed Stripping Level: High (용량 감소)
```

---

## 2. 에셋 최적화

### 텍스처
```
모든 텍스처 선택 → Inspector:

✅ Max Size: 512 (멀리 보이는 오브젝트)
✅ Max Size: 1024 (주요 건축물)
✅ Compression: Normal Quality
✅ Generate Mip Maps: 체크
```

### 3D 모델
```
모든 FBX 선택 → Inspector:

✅ Read/Write Enabled: 체크 해제 (메모리 절약)
✅ Optimize Mesh: 체크
✅ Mesh Compression: High
✅ Import Normals: Calculate (더 작은 파일)
```

### 오디오
```
모든 오디오 파일:

✅ Load Type: Streaming (배경음)
✅ Load Type: Compressed In Memory (효과음)
✅ Compression Format: Vorbis
✅ Quality: 70% (충분함)
```

---

## 3. 씬 최적화

### Lighting
```
Window → Rendering → Lighting:

✅ Baked Global Illumination: 체크 (런타임 부하 감소)
✅ Lightmap Resolution: 낮춤 (20 → 10)
✅ Lightmap Compression: High Quality
```

### Occlusion Culling
```
Window → Rendering → Occlusion Culling:

✅ Bake 실행
  - 안 보이는 건축물은 렌더링 안 함
  - 성능 크게 향상!
```

### LOD (Level of Detail)
```csharp
// 복잡한 건축물에 LOD 추가
GameObject building = GameObject.Find("Gyotaejeon");
LODGroup lodGroup = building.AddComponent<LODGroup>();

LOD[] lods = new LOD[3];
lods[0] = new LOD(0.6f, highDetail);  // 가까이
lods[1] = new LOD(0.3f, mediumDetail); // 중간
lods[2] = new LOD(0.1f, lowDetail);   // 멀리

lodGroup.SetLODs(lods);
```

---

## 4. 코드 최적화

### Object Pooling
```csharp
// 이미 있지만 더 공격적으로 사용
// 퀴즈 UI, 파티클 등 재사용
```

### Update() 최적화
```csharp
// BAD
void Update() {
    transform.position = player.position + offset;
}

// GOOD
void LateUpdate() {  // Update()보다 덜 자주 호출
    if (Vector3.Distance(transform.position, target) > 0.01f) {
        transform.position = Vector3.Lerp(...);
    }
}
```

### Physics 최적화
```
Edit → Project Settings → Physics:

✅ Auto Sync Transforms: 체크 해제
✅ Reuse Collision Callbacks: 체크
```

---

## 5. 빌드 크기 줄이기

### Addressables (선택사항)
```
Window → Asset Management → Addressables:

1. 큰 에셋들을 Addressable로 마크
2. Build → New Build → Default Build Script
3. 필요할 때만 동적 로드

장점:
- 초기 로딩 시간 감소
- 메모리 효율적
```

### Stripping
```
Player Settings → Other Settings:

✅ Strip Engine Code: 체크
✅ Managed Stripping Level: High
✅ Script Call Optimization: Fast but no exceptions
```

---

## 6. 데모 버전 만들기 (추천!)

### 포함할 것
```
Scenes/
├─ MainMenu (간단한 메뉴)
└─ DemoLevel (짧은 데모 맵)
   ├─ 시작 구역
   ├─ 퀴즈 3개
   ├─ 간단한 건축물 1-2개
   └─ 골 지점

제거:
- 복잡한 건축물 (교태전 전체 등)
- 여러 스테이지
- 고해상도 텍스처
```

### 새 씬 만들기
```
1. DemoLevel 씬 생성
2. 간단한 트랙만 배치
3. Build Settings → Scenes In Build
   ✅ DemoLevel만 체크
4. 빌드!
```

---

## 7. 테스트

### 로컬 테스트
```bash
# Python 간단한 서버
cd Build/WebGL/minjirun
python -m http.server 8000

# 브라우저에서
http://localhost:8000
```

### 성능 측정
```
브라우저 개발자 도구 (F12):

Performance 탭:
- 60 FPS 유지되는지 확인
- 메모리 누수 체크

Network 탭:
- 다운로드 크기 확인
- 로딩 시간 측정
```

---

## 8. 배포 (Django)

### Nginx 설정 (압축)
```nginx
location /static/unity/ {
    gzip on;
    gzip_types application/javascript application/wasm;
    gzip_comp_level 6;
    
    add_header Cache-Control "public, max-age=31536000";
}
```

### Django static 설정
```python
# settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WebGL 빌드 파일을 static/unity/minjirun/ 에 복사
```

---

## 9. 예상 결과

### 전체 버전
```
빌드 크기: 150-250MB (Brotli 압축)
로딩 시간: 3-5분 (느린 인터넷)
권장: 데스크톱 전용
```

### 최적화 버전
```
빌드 크기: 50-100MB
로딩 시간: 1-2분
권장: 데스크톱 + 태블릿
```

### 데모 버전 ⭐ (추천)
```
빌드 크기: 20-40MB
로딩 시간: 30초 - 1분
권장: 모든 기기 (홍보용으로 완벽!)
```

---

## 10. 결론

**추천 전략:**

1. **데모 버전 먼저 만들기**
   - 빠른 로딩
   - 좋은 첫인상
   - 게임 맛보기

2. **최적화 버전 (선택사항)**
   - 전체 게임 경험
   - LOD, 텍스처 압축 적용
   - 좀 더 긴 로딩 감수

3. **Windows/Mac 빌드 병행**
   - 최고 품질
   - 빠른 로딩
   - 전체 기능

**WebGL은 가능하지만, 데모 버전으로 시작하는 것을 강력 추천합니다!** 🎮

