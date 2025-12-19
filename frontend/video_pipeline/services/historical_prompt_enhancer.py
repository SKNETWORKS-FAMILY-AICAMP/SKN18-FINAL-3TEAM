"""
역사적 프롬프트 강화 모듈
- 한국어 역사 용어를 시대가 명확한 영어로 변환
- 상황에 따라 평화로운 조선/임진왜란 배경을 유동적으로 적용
- 현대 군인/무기 등장 방지
"""

# 1. 평화로운 조선 시대 배경 (기본값)
JOSEON_GENERAL_CONTEXT = """
HISTORICAL CONTEXT:
- Period: Joseon Dynasty 15th-16th century Korea (Pre-war or peaceful period)
- Architecture: Traditional Korean palace, Hanok, stone walls, wooden structures
- Atmosphere: Majestic, serene, scholarly, or daily life
- Costume: Traditional Hanbok, court official robes (Gwanbok)
- STRICT: NO modern elements, NO western buildings, NO electricity, NO concrete
"""

# 2. 임진왜란 전쟁 배경 (전투 키워드 감지 시 발동)
IMJIN_WAR_CONTEXT = """
CRITICAL HISTORICAL CONTEXT - Imjin War (1592-1598):
- Period: Joseon Dynasty 16th century Korea (War period)
- Participants: Joseon soldiers vs Japanese samurai invaders
- Atmosphere: Battlefield, smoke, tension, urgency
- Weapons: Bows, arrows, swords, spears, traditional cannons (No modern guns)
- STRICT: NO modern military, NO tanks, NO rifles, NO camouflage uniforms
"""

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
    
    # 인물
    '이순신': 'Admiral Yi Sun-sin in traditional Korean naval commander armor',
    '권율': 'General Gwon Yul in traditional Korean military commander armor',
    '세종': 'King Sejong the Great of Joseon Dynasty',
    '세종대왕': 'King Sejong the Great in royal dragon robe',
    '장영실': 'Jang Yeong-sil, historical scientist of Joseon',
    
    # 장소/지명
    '궁': 'traditional Korean palace',
    '경복궁': 'Gyeongbokgung Palace',
    '한성': 'Hanseong (Seoul) Joseon Dynasty capital city',
    '성': 'traditional Korean fortress with stone walls',
    '산성': 'traditional Korean mountain fortress',
    
    # 무기/장비
    '활': 'traditional Korean bow',
    '화살': 'traditional arrows',
    '칼': 'traditional Korean sword',
    '창': 'traditional spear',
    '총통': 'traditional Korean cannon',
    '신기전': 'Singijeon (traditional rocket arrow launcher)',
}

def detect_korean_content(text: str) -> bool:
    """텍스트에 한국어가 포함되어 있는지 확인"""
    for char in text:
        if '\uAC00' <= char <= '\uD7A3':
            return True
    return False

def translate_historical_terms(text: str) -> str:
    """한국어 역사 용어를 시대가 명확한 영어로 변환"""
    if not detect_korean_content(text):
        return text
    
    translated_text = text
    replacements = []
    
    # 길이가 긴 순서대로 변환
    sorted_terms = sorted(KOREAN_HISTORICAL_TERMS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for korean_term, english_term in sorted_terms:
        if korean_term in translated_text:
            translated_text = translated_text.replace(korean_term, english_term)
            replacements.append(f"'{korean_term}' → English Term")
    
    return translated_text

def enhance_with_historical_context(prompt: str, is_image_prompt: bool = True) -> str:
    """
    프롬프트에 조선시대 역사적 배경 추가 (전쟁 vs 평화 자동 감지)
    """
    # 1단계: 한국어 용어 변환
    enhanced = translate_historical_terms(prompt)
    prompt_lower = enhanced.lower()
    
    # 2단계: 전쟁 키워드 감지
    war_keywords = [
        'war', 'battle', 'invasion', 'fight', 'attack', 'army', 'weapon', 'soldier', 
        'kill', 'destroy', 'fire', 'explosion', 'arrow', 'cannon', 
        '전쟁', '전투', '공격', '침략'
    ]
    
    is_war_scene = any(keyword in prompt_lower for keyword in war_keywords)
    
    # 3단계: 상황에 맞는 컨텍스트 주입
    if is_war_scene:
        # 전쟁 상황
        context_suffix = IMJIN_WAR_CONTEXT
        if not is_image_prompt: # 영상용이면 더 짧게
            context_suffix = "Setting: Fierce battlefield of Imjin War. Smoke, fire, combat atmosphere."
    else:
        # 평화/일반 상황 (세종대왕 등)
        context_suffix = JOSEON_GENERAL_CONTEXT
        if not is_image_prompt: # 영상용이면 더 짧게
            context_suffix = "Setting: Peaceful Joseon Dynasty scenery. Nature, palace, quiet atmosphere."
    
    enhanced_prompt = f"{enhanced}. {context_suffix}"
    
    return enhanced_prompt

def add_anti_modern_negative_prompt() -> str:
    """현대 요소 차단용 네거티브 프롬프트"""
    return """modern soldiers, modern military, contemporary uniforms, modern weapons, guns, rifles, machine guns, tanks, helicopters, modern equipment, 20th century, 21st century, present day, contemporary clothing, modern architecture, power lines, cars, buildings, text, subtitle, watermark"""

def process_scene_prompt(scene_prompt: str, is_image: bool = True) -> tuple:
    """장면 프롬프트를 처리하여 강화된 프롬프트와 네거티브 프롬프트 반환"""
    enhanced_prompt = enhance_with_historical_context(scene_prompt, is_image_prompt=is_image)
    negative_prompt = add_anti_modern_negative_prompt()
    
    return enhanced_prompt, negative_prompt