# game_state_manager.py
import json
import os
import copy
import traceback # Added import
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
    """게임을 Vercel KV에서 로드합니다."""
    print(f"[LOAD_STATE_DEBUG] Attempting to load game state from Vercel KV.")
    print(f"[LOAD_STATE_DEBUG] Using KV_KEY: {GAME_STATE_KV_KEY}")
    try:
        state = kv.get(GAME_STATE_KV_KEY)
        if state is None:
            print(f"[LOAD_STATE_DEBUG] No state found in Vercel KV for key '{GAME_STATE_KV_KEY}'. Initializing new game state.")
            default_state_copy = copy.deepcopy(DEFAULT_GAME_STATE)
            print(f"[LOAD_STATE_DEBUG] Default state 'initial_setup_done': {default_state_copy['player_data'].get('initial_setup_done')}")
            return default_state_copy

        print(f"[LOAD_STATE_DEBUG] State found in Vercel KV. Processing...")
        # 기본값 보충
        for key, default_value in DEFAULT_GAME_STATE.items():
            if key not in state:
                print(f"[LOAD_STATE_DEBUG] Key '{key}' missing in loaded state. Initializing with default.")
                state[key] = copy.deepcopy(default_value)
            elif isinstance(default_value, dict):
                for sub_key, sub_default_value in default_value.items():
                    if sub_key not in state[key]:
                        print(f"[LOAD_STATE_DEBUG] Sub-key '{sub_key}' in '{key}' missing. Initializing with default.")
                        state[key][sub_key] = copy.deepcopy(sub_default_value)
        
        # 플레이어 데이터 상세 보충
        current_player_data = state.get("player_data", {})
        for p_key, p_default_value in DEFAULT_PLAYER_DATA.items():
            if p_key not in current_player_data:
                print(f"[LOAD_STATE_DEBUG] Player data key '{p_key}' missing. Initializing with default.")
                current_player_data[p_key] = copy.deepcopy(p_default_value)
            elif isinstance(p_default_value, dict): # nested dicts in player_data (e.g. stats)
                 for stat_key, stat_default_value in p_default_value.items():
                    if stat_key not in current_player_data[p_key]:
                         print(f"[LOAD_STATE_DEBUG] Player data sub-key '{stat_key}' in '{p_key}' missing. Initializing with default.")
                         current_player_data[p_key][stat_key] = copy.deepcopy(stat_default_value)
        state["player_data"] = current_player_data
        print(f"[LOAD_STATE_DEBUG] Processed player_data 'initial_setup_done': {state['player_data'].get('initial_setup_done')}")
        print(f"[LOAD_STATE_DEBUG] Processed player_stats: {state['player_data'].get('stats')}")

        # 히스토리 역직렬화
        if "history" in state and isinstance(state["history"], list):
            print(f"[LOAD_STATE_DEBUG] Deserializing history. Length: {len(state['history'])}")
            state["history"] = deserialize_history(state["history"])
        
        print(f"[LOAD_STATE_DEBUG] Game state loaded and processed successfully.")
        return state
    except Exception as e:
        print(f"Vercel KV에서 게임 상태 로드 중 오류 발생: {e}. 새 게임을 시작합니다.")
        print(f"[LOAD_STATE_DEBUG] Error during load_game_state: {e}")
        traceback.print_exc()
        default_state_copy_on_error = copy.deepcopy(DEFAULT_GAME_STATE)
        print(f"[LOAD_STATE_DEBUG] Returning default state due to error. 'initial_setup_done': {default_state_copy_on_error['player_data'].get('initial_setup_done')}")
        return default_state_copy_on_error

def save_game_state(state):
    """게임 상태를 Vercel KV에 저장합니다."""
    print(f"[SAVE_STATE_DEBUG] Attempting to save game state to Vercel KV.")
    if state and state.get("player_data"):
        print(f"[SAVE_STATE_DEBUG] Player data to be saved 'initial_setup_done': {state['player_data'].get('initial_setup_done')}")
        print(f"[SAVE_STATE_DEBUG] Player stats to be saved: {state['player_data'].get('stats')}")
    else:
        print(f"[SAVE_STATE_DEBUG] Player data is missing or empty in the state to be saved.")

    try:
        current_state_to_save = copy.deepcopy(state)
        if "history" in current_state_to_save:
            print(f"[SAVE_STATE_DEBUG] Serializing history before saving. Original history length: {len(current_state_to_save['history'])}")
            current_state_to_save["history"] = serialize_history(current_state_to_save["history"])
            print(f"[SAVE_STATE_DEBUG] Serialized history length: {len(current_state_to_save['history'])}")
        
        print(f"[SAVE_STATE_DEBUG] Calling KV.set with key: {GAME_STATE_KV_KEY}")
        kv.set(GAME_STATE_KV_KEY, current_state_to_save)
        print(f"[SAVE_STATE_DEBUG] KV.set call successful. Game state saved. (Key: {GAME_STATE_KV_KEY})")
    except Exception as e:
        print(f"Vercel KV에 게임 상태 저장 중 오류 발생: {e}")
        print(f"[SAVE_STATE_DEBUG] Error during save_game_state: {e}")
        traceback.print_exc()
