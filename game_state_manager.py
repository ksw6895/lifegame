# game_state_manager.py
import json
import os
import copy
from config import MEMORY_FILE

# === Default Game State Structures ===
DEFAULT_PLAYER_DATA = {
    "name": "플레이어",
    "level": 1,
    "xp": 0,
    "xp_to_next_level": 100,
    "gold": 0,
    "stats": {
        "힘": 5,
        "지능": 5,
        "의지력": 5,
        "체력": 5,
        "매력": 5
    },
    "stat_points": 0,
    "inventory": [],
    "active_quests": [],
    "completed_quests": [],
    "main_story_progress": {},
    "current_class": None,
    "class_buffs": {},
    "achievements": [],
    "title": None,
    "last_activity": None,
    "initial_setup_done": False
}

DEFAULT_NPCS = [
    {
        "name": "힐러 엘라",
        "description": "따뜻한 마음씨의 회복 전문가.",
        "quests": [],
        "interaction_count": 0
    },
    {
        "name": "대장장이 볼드",
        "description": "무뚝뚝하지만 실력 좋은 대장장이.",
        "quests": [],
        "interaction_count": 0
    },
    {
        "name": "지혜의 올빼미",
        "description": "숲의 현자.",
        "quests": [],
        "interaction_count": 0
    }
]

DEFAULT_SHOP_ITEMS = [
    {
        "name": "작은 HP 회복 물약",
        "cost": 20,
        "effect": "HP를 30 회복합니다.",
        "icon": "🧪"
    },
    {
        "name": "단기 집중력 부스트 포션",
        "cost": 50,
        "effect": "1시간 동안 지능 +1 버프",
        "icon": "💡"
    },
    {
        "name": "행운의 토큰",
        "cost": 100,
        "effect": "다음 퀘스트 완료 시 아이템 드랍률 소폭 증가",
        "icon": "🍀"
    }
]

DEFAULT_GAME_STATE = {
    "player_data": DEFAULT_PLAYER_DATA,
    "npcs": DEFAULT_NPCS,
    "shop_items": DEFAULT_SHOP_ITEMS,
    "game_turn": 0,
    "history": []  # Gemini 대화 기록
}

def serialize_history(history):
    """Gemini 대화 기록을 JSON 직렬화 가능한 형태로 변환"""
    serialized = []
    for item in history:
        if hasattr(item, 'role') and hasattr(item, 'parts'):
            # Content 객체를 딕셔너리로 변환
            parts_text = []
            for part in item.parts:
                if hasattr(part, 'text'):
                    parts_text.append(part.text)
                else:
                    parts_text.append(str(part))
            serialized.append({
                "role": item.role,
                "parts": parts_text
            })
        elif isinstance(item, dict):
            # 이미 딕셔너리 형태인 경우
            serialized.append(item)
    return serialized

def deserialize_history(serialized_history):
    """직렬화된 히스토리를 Content 객체로 복원"""
    from google.genai import types
    
    history = []
    for item in serialized_history:
        if isinstance(item, dict) and 'role' in item and 'parts' in item:
            parts = []
            for part_text in item['parts']:
                # Fix: Use the correct API for creating Part objects
                parts.append(types.Part(text=part_text))
            
            history.append(types.Content(
                role=item['role'],
                parts=parts
            ))
    return history

def load_game_state():
    """게임 상태를 파일에서 로드합니다."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                # 기본값 보충
                for key, default_value in DEFAULT_GAME_STATE.items():
                    if key not in state:
                        state[key] = copy.deepcopy(default_value)
                
                # 플레이어 데이터 보충
                current_player_data = state.get("player_data", {})
                for p_key, p_default_value in DEFAULT_PLAYER_DATA.items():
                    if p_key not in current_player_data:
                        current_player_data[p_key] = copy.deepcopy(p_default_value)
                state["player_data"] = current_player_data
                
                return state
        except json.JSONDecodeError:
            print(f"경고: {MEMORY_FILE} 파일이 손상되었습니다. 새 게임을 시작합니다.")
    return copy.deepcopy(DEFAULT_GAME_STATE)

def save_game_state(state):
    """게임 상태를 파일에 저장합니다."""
    # 히스토리 직렬화
    if "history" in state:
        state["history"] = serialize_history(state["history"])
    
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)