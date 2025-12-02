"""
장면 파싱 및 분석 모듈
- 프롬프트에서 sin1:, sin2: 형식 파싱
- 장면 설명과 카메라 움직임 구분
"""

import re


def parse_scenes(text):
    """sin1:, sin2: 형식의 프롬프트를 파싱하여 신 목록 반환"""
    # sin1:, sin2: 패턴으로 분리
    pattern = r'sin(\d+):\s*(.+?)(?=sin\d+:|$)'
    matches = re.findall(pattern, text, re.DOTALL)

    scenes = []
    for scene_num, scene_text in matches:
        scenes.append({
            'number': int(scene_num),
            'text': scene_text.strip()
        })

    return scenes


def separate_scene_and_camera(scene_text: str) -> tuple:
    """
    장면 설명과 카메라 움직임을 자동으로 구분
    
    Args:
        scene_text: 원본 장면 텍스트
        
    Returns:
        (장면 설명, 카메라 움직임) 튜플
    """
    # 카메라 움직임 키워드
    camera_keywords = [
        'wide shot', 'medium shot', 'close-up', 'close up', 'dynamic action shot',
        'cinematic', 'camera', 'pan', 'zoom', 'tracking', 'movement', 'shot',
        'mix', 'angle', 'framing', 'perspective'
    ]
    
    # 문장 단위로 분리
    sentences = scene_text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    scene_parts = []
    camera_parts = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        # 카메라 움직임 키워드가 포함되어 있으면 카메라 움직임으로 분류
        if any(keyword in sentence_lower for keyword in camera_keywords):
            camera_parts.append(sentence)
        else:
            scene_parts.append(sentence)
    
    scene_description = '. '.join(scene_parts) if scene_parts else ""
    camera_movement = '. '.join(camera_parts) if camera_parts else ""
    
    # 카메라 움직임이 없으면 기본값 추가
    if not camera_movement:
        camera_movement = "smooth camera movement, cinematic, gentle motion"
    
    return scene_description, camera_movement

