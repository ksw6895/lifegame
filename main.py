# main.py
"""
인생 RPG 게임 - Life is Game
Gemini 2.5 Flash + DALL-E 3 기반 개인용 RPG 게임

필요한 라이브러리:
pip install google-generativeai python-dotenv pillow requests

.env 파일 설정:
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
"""

import sys
import os
from tkinter import messagebox

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """메인 함수"""
    try:
        # GUI 클래스 import 및 실행
        from rpg_gui import RPGGameGUI
        
        # 게임 인스턴스 생성 및 실행
        game = RPGGameGUI()
        game.run()
        
    except ImportError as e:
        print(f"필수 라이브러리가 설치되지 않았습니다: {e}")
        print("\n다음 명령어로 라이브러리를 설치하세요:")
        print("pip install google-generativeai python-dotenv pillow requests")
        sys.exit(1)
        
    except Exception as e:
        print(f"프로그램 실행 중 오류가 발생했습니다: {e}")
        # GUI가 이미 실행 중인 경우 tkinter를 사용하여 오류 표시
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()  # 메인 윈도우 숨기기
            messagebox.showerror("오류", f"프로그램 실행 중 오류가 발생했습니다:\n{str(e)}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()