# gemini_client.py
from google import genai
from google.genai import types
from .config import GEMINI_API_KEY, GEMINI_MODEL_NAME, THINKING_BUDGET

# GM 기본 프롬프트
BASE_GM_PROMPT = """
> 역할
당신은 플레이어의 "인생 RPG" 게임 마스터(GM)입니다. 플레이어의 일상과 목표를 게임화하여 동기부여와 즐거움을 제공하세요.

# 중요한 규칙
1. 모든 대화는 친절하고 격려적인 톤으로 진행합니다.
2. 플레이어의 현재 상태(레벨, XP, 골드, 능력치)를 항상 인지하고 반영합니다.
3. 퀘스트 완료 시 구체적인 보상을 명시합니다 (예: XP +30, 골드 +15).
4. 아이템 드랍 시 반드시 "(이미지 생성: [아이템 이름], 게임 아이템 카드 스타일, 판타지풍, 빛나는 효과)" 형식을 포함합니다.
5. 【SYSTEM】과 【GM】 태그를 적절히 사용하여 시스템 메시지와 GM 대사를 구분합니다.

# 퀘스트 관리 시스템 (매우 중요!)
당신은 플레이어의 퀘스트를 직접 생성하고 관리할 권한이 있습니다. 다음 형식을 사용하세요:

## 퀘스트 추가 시:
[QUEST_ADD: 퀘스트이름 | 설명 | 상태]
예: [QUEST_ADD: 퀀트 강의 7과 완강 | 퀀트 이론의 심화 학습 | 진행중]

## 퀘스트 완료 시:
[QUEST_COMPLETE: 퀘스트이름]
예: [QUEST_COMPLETE: 퀀트 강의 7과 완강]

## 퀘스트 업데이트 시:
[QUEST_UPDATE: 퀘스트이름 | 새로운상태 | 새로운설명]
예: [QUEST_UPDATE: 헬스장 운동 | 2/4 완료 | 이번 주 4회 목표 중 2회 완료]

## 보상 지급 시:
[REWARD: XP +30, 골드 +15, 아이템: 지식의 파편]

# 초기 설정 안내
플레이어가 처음 시작할 때:
1. 친절하게 인사하고 게임 시스템을 간단히 설명합니다.
2. 현재 기본 능력치를 보여주고, 성장 가능성을 설명합니다.
3. 이번 주의 목표를 물어봅니다.
4. 입력받은 목표를 창의적인 퀘스트로 변환하고 [QUEST_ADD] 태그로 추가합니다.

# 게임 시스템
- 레벨업: XP가 필요량에 도달하면 레벨업, 능력치 포인트 +3 획득
- 퀘스트: 현실 과제를 몬스터나 퀘스트로 변환 (당신이 직접 관리)
- 상점: 골드로 아이템 구매 가능
- NPC: 힐러 엘라, 대장장이 볼드, 지혜의 올빼미와 상호작용
- 전직: 레벨 5, 10에서 직업 선택 가능

항상 플레이어를 격려하고 게임을 즐길 수 있도록 도와주세요!
"""

INITIAL_HISTORY = [
    types.Content(
        role='user',
        parts=[types.Part(text=BASE_GM_PROMPT)]
    ),
    types.Content(
        role='model', 
        parts=[types.Part(text="【GM】 안녕하세요, 모험가님! 인생 RPG의 세계에 오신 것을 환영합니다! 저는 당신의 여정을 함께할 게임 마스터입니다. 😊")]
    )
]

_client_instance = None

def get_gemini_client():
    """Gemini 클라이언트 인스턴스를 가져옵니다."""
    global _client_instance
    if _client_instance is None and GEMINI_API_KEY:
        _client_instance = genai.Client(api_key=GEMINI_API_KEY)
    return _client_instance

def get_gm_response(client, user_prompt_with_context, history=None):
    """GM 응답을 받아옵니다."""
    if not client:
        return "【GM】 Gemini 클라이언트가 초기화되지 않았습니다.", []
    
    try:
        # 전체 대화 기록 구성
        if history:
            contents = list(history)  # 기존 히스토리 복사
        else:
            contents = list(INITIAL_HISTORY)  # 초기 히스토리 사용
        
        # 사용자 메시지 추가
        contents.append(types.Content(
            role='user',
            parts=[types.Part(text=user_prompt_with_context)]
        ))
        
        # Thinking Config를 사용하여 응답 생성
        config = types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=4096,  # 2048에서 4096으로 증가하여 더 긴 퀘스트 목록 생성 허용
            thinking_config=types.ThinkingConfig(
                thinking_budget=THINKING_BUDGET
            ),
            safety_settings=[
                types.SafetySetting(
                    category='HARM_CATEGORY_HARASSMENT',
                    threshold='BLOCK_NONE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_HATE_SPEECH', 
                    threshold='BLOCK_NONE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                    threshold='BLOCK_NONE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_DANGEROUS_CONTENT',
                    threshold='BLOCK_NONE'
                )
            ]
        )
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=contents,
            config=config
        )
        
        # 응답 추가
        contents.append(types.Content(
            role='model',
            parts=[types.Part(text=response.text)]
        ))
        
        return response.text, contents
        
    except Exception as e:
        print(f"Gemini API 오류: {e}")
        error_response = f"【GM】 오류가 발생했습니다: {str(e)}"
        
        # 오류 발생 시에도 히스토리 유지
        if history:
            contents = list(history)
        else:
            contents = list(INITIAL_HISTORY)
        
        contents.append(types.Content(
            role='user',
            parts=[types.Part(text=user_prompt_with_context)]
        ))
        contents.append(types.Content(
            role='model',
            parts=[types.Part(text=error_response)]
        ))
        
        return error_response, contents
