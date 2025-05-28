# game_state_manager.py
import json
import os
import copy
from vercel_kv import kv

# === Vercel KV Configuration ===
GAME_STATE_KV_KEY = "rpg_game_state_user_default"

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
    if serialized_history: # Ensure serialized_history is not None or empty
        for item in serialized_history:
            if isinstance(item, dict) and 'role' in item and 'parts' in item:
                parts = []
                for part_text in item['parts']:
                    parts.append(types.Part(text=part_text)) # Corrected
                
                history.append(types.Content(
                    role=item['role'],
                    parts=parts
                ))
    return history

def load_game_state():
    """게임 상태를 Vercel KV에서 로드합니다."""
    try:
        state = kv.get(GAME_STATE_KV_KEY)
        if state is None:
            print("KV에서 게임 상태를 찾을 수 없습니다. 새 게임을 시작합니다.")
            return copy.deepcopy(DEFAULT_GAME_STATE)

        # 기본값 보충 (새로운 기본값이 추가되었을 경우를 대비)
        for key, default_value in DEFAULT_GAME_STATE.items():
            if key not in state:
                state[key] = copy.deepcopy(default_value)
            # Ensure nested structures like player_data also get default补충
            elif isinstance(default_value, dict):
                for sub_key, sub_default_value in default_value.items():
                    if sub_key not in state[key]:
                        state[key][sub_key] = copy.deepcopy(sub_default_value)
        
        # 플레이어 데이터 상세 보충
        current_player_data = state.get("player_data", {})
        for p_key, p_default_value in DEFAULT_PLAYER_DATA.items():
            if p_key not in current_player_data:
                current_player_data[p_key] = copy.deepcopy(p_default_value)
            elif isinstance(p_default_value, dict): # nested dicts in player_data (e.g. stats)
                 for stat_key, stat_default_value in p_default_value.items():
                    if stat_key not in current_player_data[p_key]:
                         current_player_data[p_key][stat_key] = copy.deepcopy(stat_default_value)
        state["player_data"] = current_player_data

        # 히스토리 역직렬화
        if "history" in state and isinstance(state["history"], list):
            state["history"] = deserialize_history(state["history"])
        
        return state
    except Exception as e:
        print(f"Vercel KV에서 게임 상태 로드 중 오류 발생: {e}. 새 게임을 시작합니다.")
        return copy.deepcopy(DEFAULT_GAME_STATE)

def save_game_state(state):
    """게임 상태를 Vercel KV에 저장합니다."""
    try:
        # 히스토리 직렬화 (저장 전에 항상 수행)
        current_state_to_save = copy.deepcopy(state) # KV에 저장하기 전에 상태 복사
        if "history" in current_state_to_save:
            current_state_to_save["history"] = serialize_history(current_state_to_save["history"])
        
        kv.set(GAME_STATE_KV_KEY, current_state_to_save)
        print(f"게임 상태가 Vercel KV에 저장되었습니다. (Key: {GAME_STATE_KV_KEY})")
    except Exception as e:
        print(f"Vercel KV에 게임 상태 저장 중 오류 발생: {e}")
