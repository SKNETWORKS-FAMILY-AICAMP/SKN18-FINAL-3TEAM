# 폰트 파일 설치 가이드

## 필요한 폰트 파일

다음 폰트 파일들을 다운로드하여 이 폴더(`public/fonts/`)에 배치하세요:

### 1. ChosunCentennial (영상 제목용)
- 다운로드: https://fontdown.chosun.com/100/ChosunCentennial_otf2.zip
- 압축 해제 후 `ChosunCentennial_otf.otf` 파일을 이 폴더에 복사
- 최종 경로: `public/fonts/ChosunCentennial.otf`

### 2. ChosunNm (댓글용)
- 다운로드: https://fontdown.chosun.com/100/ChosunNm.zip
- 압축 해제 후 `.ttf` 파일을 이 폴더에 복사
- 최종 경로: `public/fonts/ChosunNm.ttf`

## 설치 방법

```bash
# 1. fonts 폴더로 이동
cd frontend/react/public/fonts

# 2. ChosunCentennial 다운로드 및 압축 해제
curl -L https://fontdown.chosun.com/100/ChosunCentennial_otf2.zip -o ChosunCentennial.zip
unzip ChosunCentennial.zip
# 압축 해제된 파일 중 ChosunCentennial_otf.otf를 ChosunCentennial.otf로 이름 변경

# 3. ChosunNm 다운로드 및 압축 해제
curl -L https://fontdown.chosun.com/100/ChosunNm.zip -o ChosunNm.zip
unzip ChosunNm.zip
# 압축 해제된 .ttf 파일을 ChosunNm.ttf로 이름 변경
```

## 폰트 파일 구조

```
public/
└── fonts/
    ├── ChosunCentennial.otf  (영상 제목)
    └── ChosunNm.ttf          (댓글)
```

## 참고

- 폰트 파일이 없어도 시스템 기본 폰트로 대체되어 작동합니다.
- 부크크 명조 폰트는 `index.html`에서 CDN으로 로드됩니다.

