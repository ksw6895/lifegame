from fastapi import FastAPI, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import copy

# Assuming these modules are in the same directory or properly installed
from . import game_state_manager as gsm
from . import gemini_client as gem_client_module # Renamed to avoid conflict
from . import openai_image_client
from . import game_logic
# from .config import GEMINI_API_KEY, OPENAI_API_KEY # Not directly used here if clients handle them

# --- Pydantic Models ---

class PlayerMessage(BaseModel):
    message: str
    # user_id: Optional[str] = None # Future consideration

class StatAllocation(BaseModel):
    stats: Dict[str, int] = Field(..., example={"힘": 10, "지능": 10, "의지력": 10, "체력": 10, "매력": 10})

class GameStateBase(BaseModel): # Common fields for game state
    player_data: Dict[str, Any]
    # Add other relevant game state parts if needed, e.g., game_turn, npcs
    game_turn: int
    npcs: List[Dict[str, Any]]
    shop_items: List[Dict[str, Any]]

class GameStateResponse(GameStateBase):
    history: List[Dict[str, Any]] # Serialized history

class SendMessageResponse(BaseModel):
    gm_response: str
    player_data: Dict[str, Any]
    quest_updates: Optional[List[str]] = None # Made optional as per game_logic.parse_gm_response
    image_url: Optional[str] = None
    new_achievements: Optional[List[str]] = None # Made optional as per game_logic.check_achievements
    command_response: Optional[str] = None # For direct command output

# --- FastAPI App Initialization ---
app = FastAPI()

# Initialize Gemini client
gemini_initialized_client = gem_client_module.get_gemini_client()
if not gemini_initialized_client:
    # This print will go to server logs. Consider a more robust way to handle this.
    print("CRITICAL ERROR: Gemini client could not be initialized. Check API key and configuration.")
    # Depending on server setup, may want to raise an exception to stop startup
    # raise RuntimeError("Gemini client failed to initialize.")

# --- Helper Functions ---

def build_gemini_context(user_input: str, player_data: Dict[str, Any], game_state: Dict[str, Any]) -> str:
    """
    Constructs the detailed prompt context for Gemini based on the current game state.
    This is a simplified adaptation. A real implementation would be more complex.
    """
    # Basic context - can be greatly expanded
    context = f"플레이어 이름: {player_data.get('name', '알 수 없음')}\n"
    context += f"레벨: {player_data.get('level', 1)}\n"
    context += f"경험치: {player_data.get('xp', 0)} / {player_data.get('xp_to_next_level', 100)}\n"
    context += f"골드: {player_data.get('gold', 0)}\n"
    context += "능력치:\n"
    for stat, value in player_data.get('stats', {}).items():
        context += f"  {stat}: {value}\n"
    
    context += f"현재 클래스: {player_data.get('current_class', '없음')}\n"
    
    active_quests = player_data.get('active_quests', [])
    if active_quests:
        context += "진행 중인 퀘스트:\n"
        for quest in active_quests:
            context += f"  - {quest.get('name', '이름 없는 퀘스트')}: {quest.get('description', '')}\n"
            
    # Include recent history if it helps Gemini understand flow (e.g. last few turns)
    # For now, history is managed by gemini_client directly.
    # If specific parts of history are needed for context, they could be extracted here.

    # Include current game turn
    context += f"현재 게임 턴: {game_state.get('game_turn', 0)}\n"

    # The user's direct input
    context += f"\n플레이어의 현재 행동 또는 대화: '{user_input}'\n"
    
    # General instruction to the LLM
    context += "\n당신은 이 게임의 GM(게임 마스터)입니다. 플레이어의 행동에 따라 게임 세계를 묘사하고, NPC와 대화하며, 퀘스트를 진행하고, 전투를 관리해주세요. 상세하고 창의적인 답변을 생성해주세요. 필요한 경우 JSON 형식으로 게임 상태 변경을 지시할 수 있습니다 (예: {\"action\": \"add_item\", \"item_name\": \"HP 포션\"})."
    
    return context

# --- API Endpoints ---

@app.post("/api/game/initialize", response_model=GameStateResponse)
async def initialize_game():
    """
    Initializes the game state or loads an existing one.
    Returns the current game state, including player data and serialized history.
    """
    try:
        game_state = await run_in_threadpool(gsm.load_game_state)
        # load_game_state already deserializes history, so we need to re-serialize for response.
        # However, our Pydantic model expects serialized history (List[Dict]).
        # gsm.serialize_history is available if needed, but load_game_state should return
        # history in a format that's ready for Pydantic after deserialization.
        # Let's assume gsm.load_game_state returns history as List[Content]
        # and gsm.serialize_history converts it to List[Dict]
        
        # The history from load_game_state is already deserialized Content objects.
        # For the response, it needs to be a list of dicts.
        serialized_history_for_response = gsm.serialize_history(game_state["history"])

        # Ensure all parts of DEFAULT_GAME_STATE are present
        response_data = {
            "player_data": game_state.get("player_data", gsm.DEFAULT_PLAYER_DATA),
            "history": serialized_history_for_response,
            "game_turn": game_state.get("game_turn", gsm.DEFAULT_GAME_STATE["game_turn"]),
            "npcs": game_state.get("npcs", gsm.DEFAULT_NPCS),
            "shop_items": game_state.get("shop_items", gsm.DEFAULT_SHOP_ITEMS),
        }
        return GameStateResponse(**response_data)
    except Exception as e:
        print(f"Error initializing game: {e}") # Log error
        raise HTTPException(status_code=500, detail=f"게임 초기화 중 오류 발생: {str(e)}")


@app.get("/api/game/state", response_model=GameStateResponse)
async def get_game_state():
    """
    Retrieves the current game state.
    """
    try:
        game_state = await run_in_threadpool(gsm.load_game_state)
        serialized_history_for_response = gsm.serialize_history(game_state["history"])
        
        response_data = {
            "player_data": game_state.get("player_data", gsm.DEFAULT_PLAYER_DATA),
            "history": serialized_history_for_response,
            "game_turn": game_state.get("game_turn", gsm.DEFAULT_GAME_STATE["game_turn"]),
            "npcs": game_state.get("npcs", gsm.DEFAULT_NPCS),
            "shop_items": game_state.get("shop_items", gsm.DEFAULT_SHOP_ITEMS),
        }
        return GameStateResponse(**response_data)
    except Exception as e:
        print(f"Error getting game state: {e}") # Log error
        raise HTTPException(status_code=500, detail=f"게임 상태 로드 중 오류 발생: {str(e)}")

@app.post("/api/game/character_creation", response_model=Dict[str, Any])
async def create_character(payload: StatAllocation):
    """
    Sets the initial stats for the player character.
    Assumes basic validation for now.
    """
    game_state = await run_in_threadpool(gsm.load_game_state)
    player_data = game_state.get("player_data")

    if player_data.get("initial_setup_done", False):
         raise HTTPException(status_code=400, detail="캐릭터 초기 설정이 이미 완료되었습니다.")

    # Basic validation (example: total points, individual stat range)
    # This should ideally be more robust, perhaps in game_logic.py
    total_points = sum(payload.stats.values())
    # Assuming a total of 50 points for default stats (5 stats * 10 average)
    # This needs to align with how stat_points are awarded or if it's a fixed distribution
    expected_total = sum(gsm.DEFAULT_PLAYER_DATA["stats"].values()) # Or a fixed value like 50
    
    if total_points != expected_total : # Simplified check
         raise HTTPException(status_code=400, detail=f"능력치 총합이 {expected_total}여야 합니다. 현재: {total_points}")
    for stat, value in payload.stats.items():
        if not (1 <= value <= 15): # Example range
            raise HTTPException(status_code=400, detail=f"능력치 '{stat}'의 값은 1에서 15 사이여야 합니다.")
        if stat not in player_data["stats"]:
            raise HTTPException(status_code=400, detail=f"알 수 없는 능력치: {stat}")

    player_data["stats"] = payload.stats
    player_data["stat_points"] = 0 # Assuming all points are allocated
    player_data["initial_setup_done"] = True # Mark setup as done
    game_state["player_data"] = player_data

    await run_in_threadpool(gsm.save_game_state, game_state)
    return player_data


@app.post("/api/game/reset", response_model=Dict[str, str])
async def reset_game():
    """
    Resets the game state to its default.
    """
    try:
        # Create a deep copy of the default state to avoid modifying the constant
        game_state_to_save = copy.deepcopy(gsm.DEFAULT_GAME_STATE)
        # Ensure history is in the correct format (empty list of dicts if needed by save_game_state's serialize)
        # DEFAULT_GAME_STATE['history'] is already an empty list, which is fine.
        # serialize_history will handle it if it's Content objects or dicts.
        await run_in_threadpool(gsm.save_game_state, game_state_to_save)
        return {"message": "게임이 성공적으로 초기화되었습니다."}
    except Exception as e:
        print(f"Error resetting game: {e}") # Log error
        raise HTTPException(status_code=500, detail=f"게임 초기화 중 오류 발생: {str(e)}")


@app.post("/api/game/send_message", response_model=SendMessageResponse)
async def send_message(payload: PlayerMessage):
    """
    Processes a player's message, interacts with the game logic and Gemini,
    and returns the game's response.
    """
    if not gemini_initialized_client:
        raise HTTPException(status_code=503, detail="Gemini 클라이언트가 초기화되지 않았습니다. 서버 로그를 확인해주세요.")

    game_state = await run_in_threadpool(gsm.load_game_state)
    
    # Prevent interaction if character creation is not done
    if not game_state.get("player_data", {}).get("initial_setup_done", False) and not payload.message.startswith("/"):
        # Allow commands like /스탯초기화 or /시작 before character creation
        # This logic might need refinement based on exact commands available pre-setup
        # For now, we assume character creation is a blocking step for most interactions.
        # A more robust solution would be specific command handling or a state machine.
         if payload.message not in ["/도움말", "/시작", "/스탯초기화"]: # Example allowed commands
            raise HTTPException(status_code=400, detail="캐릭터 초기 설정을 먼저 완료해주세요. '/시작' 명령어를 사용하거나 스탯을 분배하세요.")


    game_state["game_turn"] = game_state.get("game_turn", 0) + 1
    player_input = payload.message

    # 1. Process Command
    command_response_text, is_command = game_logic.process_command(player_input, game_state["player_data"], game_state)
    
    if is_command:
        if command_response_text is not None:
            # Some commands might modify state (e.g., /equip), others just return info (/stat)
            # process_command should handle state changes internally if they are simple,
            # or return data for main endpoint to handle.
            # For now, assume process_command updates game_state["player_data"] if necessary.
            await run_in_threadpool(gsm.save_game_state, game_state) # Save if command changed state
            return SendMessageResponse(
                gm_response="", # No GM response for commands unless it's info
                player_data=game_state["player_data"],
                command_response=command_response_text,
                # quest_updates, image_url, new_achievements can be None or empty
            )
        else: # Command was processed but returned no text (e.g. internal state change)
            await run_in_threadpool(gsm.save_game_state, game_state)
            return SendMessageResponse(
                gm_response="명령이 처리되었습니다.", # Generic confirmation
                player_data=game_state["player_data"],
            )

    # 2. Build Context for Gemini (if not a command that fully handled the turn)
    # game_state["history"] here is List[Content] from load_game_state
    context = build_gemini_context(player_input, game_state["player_data"], game_state)

    # 3. Get GM Response (Ensure non-blocking)
    try:
        # gemini_client.get_gm_response is synchronous, so run in threadpool
        raw_gm_response, updated_history_content_objects = await run_in_threadpool(
            gem_client_module.get_gm_response,
            gemini_initialized_client, 
            context, 
            game_state["history"] # Pass Content objects (which are fine for threadpool)
        )
        game_state["history"] = updated_history_content_objects # Store Content objects
    except Exception as e:
        print(f"Error getting GM response from Gemini: {e}")
        raise HTTPException(status_code=503, detail=f"Gemini API 통신 중 오류: {str(e)}")

    # 4. Parse GM Response & Update Game Logic
    # parse_gm_response_for_updates might modify game_state["player_data"] directly
    updates_from_gm = game_logic.parse_gm_response_for_updates(raw_gm_response, game_state["player_data"], game_state)

    # 5. Image Generation (Async, if needed)
    image_url: Optional[str] = None
    image_prompt = game_logic.extract_image_prompt(raw_gm_response)
    if image_prompt:
        try:
            # Use run_in_threadpool for the synchronous openai_image_client.generate_image
            image_url, img_error = await run_in_threadpool(openai_image_client.generate_image, image_prompt)
            if img_error:
                print(f"OpenAI Image Generation Error: {img_error}") # Log error
                # Optionally, inform user about image error, but not critical for gameplay
            elif image_url:
                 print(f"Generated image URL: {image_url}")
        except Exception as e:
            print(f"Error during image generation call: {e}")


    # 6. Check Achievements
    # check_achievements might modify game_state["player_data"] (e.g., add to 'achievements' list)
    new_achievements = game_logic.check_achievements(game_state["player_data"], game_state)

    # 7. Save Game State
    # History is already updated with Content objects. save_game_state will serialize it.
    await run_in_threadpool(gsm.save_game_state, game_state)

    # 8. Return Response
    return SendMessageResponse(
        gm_response=raw_gm_response,
        player_data=game_state["player_data"],
        quest_updates=updates_from_gm.get("quests", []) if updates_from_gm else [], # Example structure
        image_url=image_url,
        new_achievements=new_achievements
    )

# --- Optional: Add more utility endpoints or WebSocket for real-time ---

if __name__ == "__main__":
    import uvicorn
    # This is for local development. For Vercel, this part is not used.
    # Vercel uses the `app` object directly.
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
