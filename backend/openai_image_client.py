# openai_image_client.py
import requests
import os # os.path is still used for blob pathname construction
import hashlib
import base64
from vercel_blob import put, head as vercel_head
from config import (
    OPENAI_API_KEY, OPENAI_IMAGE_MODEL, OPENAI_IMAGE_API_URL,
    DEFAULT_IMAGE_SIZE, DEFAULT_NUM_IMAGES, DEFAULT_IMAGE_QUALITY
    # IMAGE_CACHE_DIR is removed as it's no longer used
)

def generate_image(prompt_text):
    """OpenAI GPT-Image-1을 사용하여 이미지를 생성하고 Vercel Blob에 캐시합니다."""
    if not OPENAI_API_KEY:
        return None, "OpenAI API 키가 설정되지 않았습니다."

    prompt_hash = hashlib.md5(prompt_text.encode()).hexdigest()
    blob_pathname = f"cached_images/{prompt_hash}.png"

    # Vercel Blob 캐시 확인
    try:
        head_result = vercel_head(blob_pathname)
        if head_result:
            print(f"이미지 캐시 히트 (Vercel Blob): {head_result['url']}")
            return head_result['url'], None
    except Exception as e: # Typically, vercel_blob.errors.NotFoundError if not found
        if "NotFoundError" in str(type(e)) or "BlobNotFoundError" in str(type(e)) or (hasattr(e, 'status_code') and e.status_code == 404):
            print(f"이미지 캐시 미스 (Vercel Blob): {blob_pathname}")
        else:
            print(f"Vercel Blob 캐시 확인 중 오류: {e}")
            # Continue to generate image, but log this error

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
            if data.get("data") and len(data["data"]) > 0 and data["data"][0].get("b64_json"):
                image_b64 = data["data"][0]["b64_json"]
                image_data = base64.b64decode(image_b64)
                
                # Vercel Blob에 업로드
                try:
                    blob_result = put(pathname=blob_pathname, body=image_data, add_random_suffix=False)
                    print(f"이미지 업로드 성공 (Vercel Blob): {blob_result['url']}")
                    return blob_result['url'], None
                except Exception as e:
                    return None, f"Vercel Blob 업로드 실패: {str(e)}"
            else:
                # Fallback for URL response, though b64_json is expected
                if data.get("data") and len(data["data"]) > 0 and data["data"][0].get("url"):
                    image_url_from_openai = data["data"][0]["url"]
                    # To store in Vercel Blob, we need the image bytes
                    img_response = requests.get(image_url_from_openai, timeout=30)
                    if img_response.status_code == 200:
                        image_data_from_url = img_response.content
                        try:
                            blob_result = put(pathname=blob_pathname, body=image_data_from_url, add_random_suffix=False)
                            print(f"이미지(URL fallback) 업로드 성공 (Vercel Blob): {blob_result['url']}")
                            return blob_result['url'], None
                        except Exception as e:
                            return None, f"Vercel Blob 업로드 실패 (URL fallback): {str(e)}"
                    else:
                        return None, f"OpenAI URL에서 이미지 다운로드 실패: {img_response.status_code}"
                return None, "이미지 데이터(b64_json)를 OpenAI 응답에서 찾을 수 없습니다."
        else:
            error_msg = f"OpenAI API 오류 {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
                    print(f"OpenAI API 오류 상세: {error_data}") # 디버깅용 상세 오류
            except:
                 # 응답이 JSON이 아닐 수 있음
                print(f"OpenAI API 응답 파싱 실패. 상태 코드: {response.status_code}, 응답: {response.text[:500]}")
            return None, error_msg
    except requests.exceptions.Timeout:
        return None, "OpenAI 이미지 생성 시간 초과"
    except Exception as e:
        return None, f"OpenAI 이미지 생성 중 알 수 없는 오류: {str(e)}"

# The following functions are removed as they operate on the old local cache.
# def get_cached_images():
#     """캐시된 이미지 목록을 반환합니다."""
#     # Vercel Blob listing might be different, e.g., using list_blobs(prefix="cached_images/")
#     # This function is out of scope for the current refactoring.
#     return []

# def clear_image_cache():
#     """이미지 캐시를 삭제합니다."""
#     # Vercel Blob deletion would use del_blobs or similar.
#     # This function is out of scope for the current refactoring.
#     pass