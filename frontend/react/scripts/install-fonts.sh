#!/bin/bash

# 폰트 설치 스크립트
# 조선일보 폰트를 다운로드하여 public/fonts 폴더에 설치합니다.
# npm install 실행 시 자동으로 실행됩니다.

# 스크립트 위치에서 프로젝트 루트로 이동
cd "$(dirname "$0")/.." || exit

FONTS_DIR="public/fonts"
TEMP_DIR=".temp_fonts"

# 폰트 디렉토리 생성
mkdir -p "$FONTS_DIR"
mkdir -p "$TEMP_DIR"

echo "조선일보 폰트 다운로드 중..."

# ChosunCentennial 다운로드
echo "1. ChosunCentennial 다운로드 중..."
curl -L "https://fontdown.chosun.com/100/ChosunCentennial_otf2.zip" -o "$TEMP_DIR/ChosunCentennial.zip"

if [ -f "$TEMP_DIR/ChosunCentennial.zip" ]; then
  unzip -q "$TEMP_DIR/ChosunCentennial.zip" -d "$TEMP_DIR/ChosunCentennial"
  # 압축 해제된 파일 찾기
  if [ -f "$TEMP_DIR/ChosunCentennial/ChosunCentennial_otf.otf" ]; then
    cp "$TEMP_DIR/ChosunCentennial/ChosunCentennial_otf.otf" "$FONTS_DIR/ChosunCentennial.otf"
    echo "   ✓ ChosunCentennial.otf 설치 완료"
  else
    echo "   ✗ ChosunCentennial 파일을 찾을 수 없습니다."
  fi
else
  echo "   ✗ ChosunCentennial 다운로드 실패"
fi

# ChosunNm 다운로드
echo "2. ChosunNm 다운로드 중..."
curl -L "https://fontdown.chosun.com/100/ChosunNm.zip" -o "$TEMP_DIR/ChosunNm.zip"

if [ -f "$TEMP_DIR/ChosunNm.zip" ]; then
  unzip -q "$TEMP_DIR/ChosunNm.zip" -d "$TEMP_DIR/ChosunNm"
  # .ttf 파일 찾기
  TTF_FILE=$(find "$TEMP_DIR/ChosunNm" -name "*.ttf" | head -1)
  if [ -n "$TTF_FILE" ]; then
    cp "$TTF_FILE" "$FONTS_DIR/ChosunNm.ttf"
    echo "   ✓ ChosunNm.ttf 설치 완료"
  else
    echo "   ✗ ChosunNm 파일을 찾을 수 없습니다."
  fi
else
  echo "   ✗ ChosunNm 다운로드 실패"
fi

# 임시 파일 정리
rm -rf "$TEMP_DIR"

echo ""
echo "폰트 설치 완료!"
echo "설치된 폰트:"
ls -lh "$FONTS_DIR" 2>/dev/null || echo "폰트 파일이 없습니다."

