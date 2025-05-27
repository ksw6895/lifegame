# config.py
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# === API Keys ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === File Paths ===
MEMORY_FILE = "game_data.json"
IMAGE_CACHE_DIR = "cached_images"

# === Gemini Model Configuration ===
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20"  # 최신 버전 (2025년 5월)
THINKING_BUDGET = 1024  # 추론 예산 설정 (0-24576)

# === OpenAI Image Model Configuration ===
OPENAI_IMAGE_MODEL = "gpt-image-1"  # 최신 GPT-4o 기반 이미지 생성 모델
OPENAI_IMAGE_API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_NUM_IMAGES = 1
DEFAULT_IMAGE_QUALITY = "low"  # gpt-image-1 지원값: low, medium, high, auto

# === UI Configuration ===
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
CHAT_DISPLAY_WIDTH = 80
CHAT_DISPLAY_HEIGHT = 25

# === Error Handling & Validation ===
def check_api_keys():
    """API 키가 설정되어 있는지 확인합니다."""
    if not GEMINI_API_KEY:
        print("오류: GEMINI_API_KEY 환경 변수를 찾을 수 없습니다. .env 파일을 확인해주세요.")
        return False
    if not OPENAI_API_KEY:
        print("오류: OPENAI_API_KEY 환경 변수를 찾을 수 없습니다. .env 파일을 확인해주세요.")
        return False
    return True

# 이미지 캐시 디렉토리 생성
if not os.path.exists(IMAGE_CACHE_DIR):
    os.makedirs(IMAGE_CACHE_DIR)