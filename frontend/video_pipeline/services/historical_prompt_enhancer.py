"""
역사적 프롬프트 강화 모듈
- 한국어 역사 용어를 시대가 명확한 영어로 변환
- 임진왜란 배경을 정확하게 인식하도록 프롬프트 보강
- 현대 군인/무기 등장 방지
"""


# 임진왜란 (1592-1598) 역사적 배경 정보
IMJIN_WAR_CONTEXT = """CRITICAL HISTORICAL CONTEXT - Imjin War (1592-1598):
- Period: Joseon Dynasty 16th century Korea (1592-1598 war period)
- Korean side: Joseon Dynasty soldiers in traditional Korean armor (두정갑, 찰갑, traditional helmet 투구)
- Japanese side: 16th century Japanese samurai in traditional samurai armor and equipment
- Weapons: Traditional weapons ONLY (bows, arrows, swords, spears, polearms, NO guns except matchlock arquebus)
- Architecture: Traditional Korean fortress architecture (석성, wooden gates, watchtowers)
- Setting: Historical battlefield, fortress, coastal areas of Korea
- STRICT: NO modern military, NO modern weapons, NO contemporary clothing, NO 20th/21st century elements
- Time period: 16th century East Asia ONLY"""


# 한국어 → 시대 명확한 영어 변환 사전
KOREAN_HISTORICAL_TERMS = {
    # 전쟁/전투
    '임진왜란': 'Imjin War 1592-1598 Japanese invasion of Korea',
    '왜란': 'Japanese invasion war of 1592-1598',
    '전투': '16th century historical battle',
    '전쟁': '16th century war',
    '공격': 'historical military attack',
    '방어': 'historical defense',
    '침략': '16th century invasion',
    '함락': 'fall of fortress in 16th century',
    '승전': 'historical victory',
    '대첩': 'great historical victory battle',
    '격전': 'fierce historical battle',
    
    # 군대/병사
    '조선군': 'Joseon Dynasty Korean soldiers in traditional Korean armor',
    '일본군': '16th century Japanese invasion forces in traditional samurai armor',
    '왜군': '16th century Japanese samurai invaders in traditional armor',
    '병사': 'historical warriors in traditional armor',
    '군사': 'historical soldiers in period-appropriate armor',
    '군인': '16th century soldiers',
    '장군': 'historical Korean general in traditional armor',
    '무사': '16th century warrior in traditional equipment',
    '사무라이': '16th century samurai warrior',
    
    # 인물 (임진왜란 주요 인물)
    '이순신': 'Admiral Yi Sun-sin in traditional Korean naval commander armor',
    '권율': 'General Gwon Yul in traditional Korean military commander armor',
    '김시민': 'General Kim Si-min in traditional Korean commander armor',
    
    # 장소/지명
    '부산진': 'Busanjin Fortress traditional Korean fortification',
    '동래성': 'Dongnae Fortress traditional Korean stone fortress',
    '상주': 'Sangju traditional Korean fortress area',
    '행주산성': 'Haengju Mountain Fortress traditional Korean fortification',
    '진주성': 'Jinju Fortress traditional Korean castle',
    '한성': 'Hanseong (Seoul) Joseon Dynasty capital city',
    '평양성': 'Pyongyang Fortress traditional Korean fortification',
    
    # 건축물/시설
    '성': 'traditional Korean fortress with stone walls',
    '산성': 'traditional Korean mountain fortress',
    '석성': 'traditional stone fortress',
    '성곽': 'traditional fortress walls',
    '성문': 'traditional Korean fortress gate',
    '망루': 'traditional watchtower',
    '진지': 'historical military position',
    
    # 무기/장비
    '활': 'traditional Korean bow',
    '화살': 'traditional arrows',
    '칼': 'traditional Korean sword',
    '검': 'traditional sword',
    '창': 'traditional spear',
    '장창': 'traditional Korean long spear',
    '갑옷': 'traditional Korean armor',
    '투구': 'traditional Korean helmet',
    '방패': 'traditional shield',
    '총통': 'traditional Korean cannon',
    '화포': 'traditional artillery',
    
    # 일반 용어
    '군복': 'traditional military clothing of 16th century',
    '군장': 'traditional military equipment',
    '깃발': 'traditional military banner',
    '진영': 'historical military camp',
}


def detect_korean_content(text: str) -> bool:
    """
    텍스트에 한국어가 포함되어 있는지 확인
    
    Args:
        text: 확인할 텍스트
    
    Returns:
        한국어 포함 여부
    """
    # 한글 유니코드 범위: AC00-D7A3
    for char in text:
        if '\uAC00' <= char <= '\uD7A3':
            return True
    return False


def translate_historical_terms(text: str) -> str:
    """
    한국어 역사 용어를 시대가 명확한 영어로 변환
    
    Args:
        text: 원본 텍스트 (한국어 포함 가능)
    
    Returns:
        변환된 텍스트
    """
    if not detect_korean_content(text):
        return text
    
    translated_text = text
    replacements = []
    
    # 길이가 긴 순서대로 변환 (부분 매칭 방지)
    sorted_terms = sorted(KOREAN_HISTORICAL_TERMS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for korean_term, english_term in sorted_terms:
        if korean_term in translated_text:
            translated_text = translated_text.replace(korean_term, english_term)
            replacements.append(f"'{korean_term}' → '{english_term[:40]}...'")
    
    if replacements:
        print(f"    🔄 한국어 역사 용어 변환:")
        for replacement in replacements[:5]:  # 처음 5개만 표시
            print(f"       {replacement}")
        if len(replacements) > 5:
            print(f"       ... 외 {len(replacements) - 5}개 더")
    
    return translated_text


def enhance_with_historical_context(prompt: str, is_image_prompt: bool = True) -> str:
    """
    프롬프트에 임진왜란 역사적 배경 추가
    
    Args:
        prompt: 원본 프롬프트
        is_image_prompt: 이미지 생성용인지 (True) 영상 생성용인지 (False)
    
    Returns:
        강화된 프롬프트
    """
    # 1단계: 한국어 용어 변환
    enhanced = translate_historical_terms(prompt)
    
    # 2단계: 역사적 배경 추가
    if is_image_prompt:
        historical_suffix = """
HISTORICAL SETTING REQUIREMENTS:
- Joseon Dynasty 16th century Korea (1592-1598 Imjin War period)
- Traditional Korean architecture (stone fortresses, wooden structures, traditional gates)
- Soldiers in authentic period armor: Korean (두정갑/찰갑), Japanese (samurai armor)
- Traditional weapons only: bows, arrows, swords, spears, traditional cannons
- 16th century East Asian warfare atmosphere
- NO modern elements: NO modern soldiers, NO modern weapons, NO contemporary clothing
- Historical accuracy in costumes, architecture, and military equipment"""
    else:
        # 영상 생성용 (더 간결하게)
        historical_suffix = """
STRICT HISTORICAL PERIOD: Joseon Dynasty 16th century Korea, Imjin War 1592-1598, traditional Korean and Japanese armor and weapons of the period, NO modern military elements whatsoever"""
    
    enhanced_prompt = f"{enhanced}. {historical_suffix}"
    
    return enhanced_prompt


def add_anti_modern_negative_prompt() -> str:
    """
    현대 요소를 차단하는 네거티브 프롬프트 반환
    
    Returns:
        현대 요소 차단용 네거티브 프롬프트
    """
    return """modern soldiers, modern military, contemporary uniforms, modern weapons, guns, rifles, machine guns, tanks, helicopters, modern equipment, 20th century, 21st century, present day, contemporary clothing, modern architecture, anachronistic elements, wrong historical period, modern military gear, tactical vest, combat helmet, camouflage uniform"""


def process_scene_prompt(scene_prompt: str, is_image: bool = True) -> tuple:
    """
    장면 프롬프트를 처리하여 강화된 프롬프트와 네거티브 프롬프트 반환
    
    Args:
        scene_prompt: 원본 장면 프롬프트
        is_image: 이미지 생성용인지 (True) 영상 생성용인지 (False)
    
    Returns:
        (강화된 프롬프트, 현대 요소 차단 네거티브 프롬프트) 튜플
    """
    enhanced_prompt = enhance_with_historical_context(scene_prompt, is_image_prompt=is_image)
    negative_prompt = add_anti_modern_negative_prompt()
    
    return enhanced_prompt, negative_prompt


# 사용 예시
if __name__ == "__main__":
    # 테스트
    test_prompts = [
        "부산진 함락. 일본군 공격과 조선군 방어가 충돌하는 순간",
        "행주대첩. 권율 장군과 조선군이 산성을 지키는 장면",
        "이순신 장군이 왜군과 해전을 벌이는 장면",
    ]
    
    print("="*60)
    print("시대 배경 인식 강화 테스트")
    print("="*60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[테스트 {i}]")
        print(f"원본: {prompt}")
        enhanced, negative = process_scene_prompt(prompt, is_image=True)
        print(f"\n강화된 프롬프트:\n{enhanced[:200]}...")
        print(f"\n네거티브 프롬프트:\n{negative[:150]}...")
        print("-"*60)

