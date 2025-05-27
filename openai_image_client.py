# openai_image_client.py
import requests
import os
import hashlib
import base64  # Base64 디코딩을 위해 추가
from PIL import Image
from io import BytesIO
from config import (
    OPENAI_API_KEY, OPENAI_IMAGE_MODEL, OPENAI_IMAGE_API_URL,
    DEFAULT_IMAGE_SIZE, DEFAULT_NUM_IMAGES, DEFAULT_IMAGE_QUALITY, IMAGE_CACHE_DIR
)

def generate_image(prompt_text):
    """OpenAI GPT-Image-1을 사용하여 이미지를 생성합니다."""
    if not OPENAI_API_KEY:
        return None, "OpenAI API 키가 설정되지 않았습니다."
    
    # 캐시 확인
    prompt_hash = hashlib.md5(prompt_text.encode()).hexdigest()
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{prompt_hash}.png")
    if os.path.exists(cache_path):
        return cache_path, None
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 게임 스타일에 맞게 프롬프트 보강
    enhanced_prompt = f"""
    {prompt_text}
    
    Style: Fantasy RPG game item card, glowing magical aura, ornate border, 
    detailed illustration, high quality digital art, vibrant colors, 
    mystical lighting effects, game UI style, professional game asset
    """
    
    payload = {
        "model": OPENAI_IMAGE_MODEL,  # config.py에서 "gpt-image-1"로 설정되어 있어야 함
        "prompt": enhanced_prompt,
        "n": DEFAULT_NUM_IMAGES,      # gpt-image-1에서 지원하는 범위 확인 필요
        "size": DEFAULT_IMAGE_SIZE,   # 예: "1024x1024"
        "quality": DEFAULT_IMAGE_QUALITY, # 예: "standard" 또는 "hd"
        "output_format": "png",       # gpt-image-1에서는 response_format 대신 output_format 사용
        # "response_format": "url",   # 이 줄을 주석 처리 - gpt-image-1에서 지원하지 않음
    }
    
    try:
        response = requests.post(OPENAI_IMAGE_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                # gpt-image-1은 b64_json 형태로 응답을 반환
                if data["data"][0].get("b64_json"):
                    image_b64 = data["data"][0]["b64_json"]
                    image_data = base64.b64decode(image_b64)
                    
                    # 이미지 저장 (캐시 경로 사용)
                    with open(cache_path, "wb") as f:
                        f.write(image_data)
                    return cache_path, None
                elif data["data"][0].get("url"):
                    # 혹시 URL 형태로 응답이 올 경우를 대비한 fallback
                    image_url = data["data"][0]["url"]
                    img_response = requests.get(image_url, timeout=30)
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        img.save(cache_path)
                        return cache_path, None
                else:
                    return None, "이미지 데이터(b64_json 또는 url)를 응답에서 찾을 수 없습니다."
        else:
            error_msg = f"OpenAI API 오류 {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
                    # 디버깅을 위한 상세 오류 정보 출력
                    print(f"OpenAI API 오류 상세: {error_data}")
            except:
                print(f"OpenAI API 응답 파싱 실패. 상태 코드: {response.status_code}, 응답: {response.text[:500]}")
            return None, error_msg
    except requests.exceptions.Timeout:
        return None, "이미지 생성 시간 초과"
    except Exception as e:
        return None, f"이미지 생성 중 오류: {str(e)}"
    
    return None, "알 수 없는 오류"

def get_cached_images():
    """캐시된 이미지 목록을 반환합니다."""
    if not os.path.exists(IMAGE_CACHE_DIR):
        return []
    
    images = []
    for filename in os.listdir(IMAGE_CACHE_DIR):
        if filename.endswith('.png'):
            images.append(os.path.join(IMAGE_CACHE_DIR, filename))
    return images

def clear_image_cache():
    """이미지 캐시를 삭제합니다."""
    if os.path.exists(IMAGE_CACHE_DIR):
        for filename in os.listdir(IMAGE_CACHE_DIR):
            if filename.endswith('.png'):
                os.remove(os.path.join(IMAGE_CACHE_DIR, filename))