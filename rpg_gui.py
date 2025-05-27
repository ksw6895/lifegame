# rpg_gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from PIL import Image, ImageTk
import threading
import queue
import sys
import copy

from config import WINDOW_WIDTH, WINDOW_HEIGHT, CHAT_DISPLAY_WIDTH, CHAT_DISPLAY_HEIGHT, check_api_keys
from game_state_manager import load_game_state, save_game_state, DEFAULT_GAME_STATE, deserialize_history
from gemini_client import get_gemini_client, get_gm_response
from openai_image_client import generate_image
from game_logic import (
    parse_gm_response_for_updates, extract_image_prompt, 
    process_command, check_achievements
)

class CharacterCreationDialog:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.result = None
        
        # 다이얼로그 창 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("캐릭터 생성")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 창을 화면 중앙에 배치
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui()
        
    def setup_ui(self):
        """캐릭터 생성 UI를 설정합니다."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="캐릭터 생성", font=('맑은 고딕', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 설명
        desc_label = ttk.Label(main_frame, text="총 25포인트를 5개 능력치에 분배하세요.\n각 능력치는 최소 1, 최대 15까지 설정 가능합니다.", 
                              font=('맑은 고딕', 10), justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))
        
        # 능력치 설정 프레임
        stats_frame = ttk.LabelFrame(main_frame, text="능력치 설정", padding="15")
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.stat_vars = {}
        self.stat_scales = {}
        
        # 각 능력치별 슬라이더
        stats_info = [
            ("힘", "물리적 능력과 근력을 나타냅니다"),
            ("지능", "학습 능력과 논리적 사고력을 나타냅니다"),
            ("의지력", "정신력과 집중력을 나타냅니다"),
            ("체력", "건강과 지구력을 나타냅니다"),
            ("매력", "사회성과 커뮤니케이션 능력을 나타냅니다")
        ]
        
        for i, (stat_name, description) in enumerate(stats_info):
            stat_frame = ttk.Frame(stats_frame)
            stat_frame.pack(fill=tk.X, pady=5)
            
            # 능력치 이름과 현재 값
            header_frame = ttk.Frame(stat_frame)
            header_frame.pack(fill=tk.X)
            
            stat_label = ttk.Label(header_frame, text=f"{stat_name}:", font=('맑은 고딕', 11, 'bold'))
            stat_label.pack(side=tk.LEFT)
            
            self.stat_vars[stat_name] = tk.IntVar(value=5)
            value_label = ttk.Label(header_frame, textvariable=self.stat_vars[stat_name], 
                                   font=('맑은 고딕', 11, 'bold'), foreground='blue')
            value_label.pack(side=tk.RIGHT)
            
            # 슬라이더 (정수값만 선택되도록 resolution=1 설정)
            scale = ttk.Scale(stat_frame, from_=1, to=15, orient=tk.HORIZONTAL, 
                             variable=self.stat_vars[stat_name], 
                             command=lambda val, name=stat_name: self.on_scale_change(val, name))
            scale.pack(fill=tk.X, pady=(5, 0))
            self.stat_scales[stat_name] = scale
            
            # 설명
            desc_label = ttk.Label(stat_frame, text=description, font=('맑은 고딕', 9), 
                                  foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(2, 0))
        
        # 남은 포인트 표시
        self.remaining_frame = ttk.Frame(stats_frame)
        self.remaining_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.remaining_label = ttk.Label(self.remaining_frame, text="남은 포인트: 0", 
                                        font=('맑은 고딕', 12, 'bold'))
        self.remaining_label.pack()
        
        # 프리셋 버튼들
        preset_frame = ttk.LabelFrame(main_frame, text="프리셋", padding="10")
        preset_frame.pack(fill=tk.X, pady=(0, 20))
        
        preset_buttons_frame = ttk.Frame(preset_frame)
        preset_buttons_frame.pack()
        
        presets = [
            ("균형형", {"힘": 5, "지능": 5, "의지력": 5, "체력": 5, "매력": 5}),
            ("지식인", {"힘": 3, "지능": 8, "의지력": 6, "체력": 4, "매력": 4}),
            ("운동선수", {"힘": 8, "지능": 3, "의지력": 5, "체력": 7, "매력": 2}),
            ("사회인", {"힘": 3, "지능": 5, "의지력": 4, "체력": 4, "매력": 9}),
            ("수행자", {"힘": 4, "지능": 4, "의지력": 9, "체력": 5, "매력": 3})
        ]
        
        for i, (name, stats) in enumerate(presets):
            btn = ttk.Button(preset_buttons_frame, text=name, 
                           command=lambda s=stats: self.apply_preset(s))
            btn.grid(row=i//3, column=i%3, padx=5, pady=2, sticky='ew')
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="취소", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        self.create_button = ttk.Button(button_frame, text="캐릭터 생성", command=self.create_character)
        self.create_button.pack(side=tk.RIGHT)
        
        # 초기 상태 업데이트
        self.update_remaining_points()
        
    def on_scale_change(self, value, stat_name):
        """슬라이더 값 변경 시 호출됩니다 (정수값으로 반올림)."""
        try:
            # 슬라이더 값을 정수로 반올림
            int_value = round(float(value))
            # 범위 체크 (1-15)
            int_value = max(1, min(15, int_value))
            
            # 현재 값과 다를 때만 업데이트 (무한 루프 방지)
            if self.stat_vars[stat_name].get() != int_value:
                self.stat_vars[stat_name].set(int_value)
            
            self.update_remaining_points()
        except (ValueError, TypeError):
            # 오류 발생 시 기본값 5로 설정
            self.stat_vars[stat_name].set(5)
            self.update_remaining_points()
    
    def on_stat_change(self, value=None):
        """능력치 변경 시 호출됩니다."""
        self.update_remaining_points()
        
    def update_remaining_points(self):
        """남은 포인트를 업데이트합니다."""
        total_used = sum(var.get() for var in self.stat_vars.values())
        remaining = 25 - total_used
        
        self.remaining_label.config(text=f"남은 포인트: {remaining}")
        
        if remaining < 0:
            self.remaining_label.config(foreground='red')
            self.create_button.config(state='disabled')
        elif remaining > 0:
            self.remaining_label.config(foreground='orange')
            self.create_button.config(state='disabled')
        else:
            self.remaining_label.config(foreground='green')
            self.create_button.config(state='normal')
    
    def apply_preset(self, preset_stats):
        """프리셋을 적용합니다."""
        for stat_name, value in preset_stats.items():
            self.stat_vars[stat_name].set(value)
        self.update_remaining_points()
    
    def create_character(self):
        """캐릭터를 생성합니다."""
        if sum(var.get() for var in self.stat_vars.values()) != 25:
            messagebox.showerror("오류", "총 포인트가 25가 되어야 합니다.")
            return
        
        self.result = {stat: var.get() for stat, var in self.stat_vars.items()}
        self.dialog.destroy()
        self.callback(self.result)
    
    def cancel(self):
        """취소합니다."""
        self.result = None
        self.dialog.destroy()
        self.callback(None)

class RPGGameGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("인생 RPG - Life is Game")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 큐 설정
        self.message_queue = queue.Queue()
        self.image_queue = queue.Queue()
        
        # 게임 상태
        self.game_state = load_game_state()
        self.player_data = self.game_state["player_data"]
        self.gemini_client = None
        self.conversation_history = []
        
        # UI 구성
        self.setup_ui()
        
        # 게임 초기화
        self.initialize_game()
        
        # 큐 처리 시작
        self.process_queues()
        
    def setup_ui(self):
        """UI를 설정합니다."""
        # 스타일 설정
        style = ttk.Style()
        style.theme_use('clam')
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽 영역 (채팅)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 채팅 디스플레이
        self.chat_display = scrolledtext.ScrolledText(
            left_frame, 
            wrap=tk.WORD, 
            width=CHAT_DISPLAY_WIDTH, 
            height=CHAT_DISPLAY_HEIGHT,
            font=('맑은 고딕', 10),
            bg='#1e1e1e',
            fg='white',
            insertbackground='white'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 태그 설정
        self.chat_display.tag_config("gm", foreground="#FFD700")
        self.chat_display.tag_config("system", foreground="#00FF00")
        self.chat_display.tag_config("player", foreground="#87CEEB")
        self.chat_display.tag_config("error", foreground="#FF6B6B")
        
        # 입력 영역
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.input_field = ttk.Entry(input_frame, font=('맑은 고딕', 10))
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_field.bind('<Return>', self.send_message)
        
        self.send_button = ttk.Button(input_frame, text="전송", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # 오른쪽 영역 (정보 패널)
        right_frame = ttk.Frame(main_frame, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # 플레이어 정보
        self.info_notebook = ttk.Notebook(right_frame)
        self.info_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 스탯 탭
        self.stats_frame = ttk.Frame(self.info_notebook)
        self.info_notebook.add(self.stats_frame, text="스탯")
        self.setup_stats_display()
        
        # 인벤토리 탭
        self.inventory_frame = ttk.Frame(self.info_notebook)
        self.info_notebook.add(self.inventory_frame, text="인벤토리")
        self.setup_inventory_display()
        
        # 퀘스트 탭
        self.quest_frame = ttk.Frame(self.info_notebook)
        self.info_notebook.add(self.quest_frame, text="퀘스트")
        self.setup_quest_display()
        
        # 이미지 표시 영역
        self.image_frame = ttk.LabelFrame(right_frame, text="아이템 이미지", padding="10")
        self.image_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.image_label = ttk.Label(self.image_frame, text="아이템 이미지가 여기에 표시됩니다")
        self.image_label.pack()
        
        # 버튼 프레임
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 캐릭터 생성 버튼
        char_create_button = ttk.Button(button_frame, text="캐릭터 생성", command=self.show_character_creation)
        char_create_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 명령어 도움말 버튼
        help_button = ttk.Button(button_frame, text="도움말", command=self.show_help)
        help_button.pack(side=tk.LEFT)
        
    def setup_stats_display(self):
        """스탯 디스플레이를 설정합니다."""
        self.stats_labels = {}
        
        # 기본 정보
        info_frame = ttk.LabelFrame(self.stats_frame, text="캐릭터 정보", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.level_label = ttk.Label(info_frame, text="레벨: 1", font=('맑은 고딕', 12, 'bold'))
        self.level_label.pack(anchor=tk.W)
        
        self.xp_label = ttk.Label(info_frame, text="XP: 0/100")
        self.xp_label.pack(anchor=tk.W)
        
        self.gold_label = ttk.Label(info_frame, text="골드: 0G")
        self.gold_label.pack(anchor=tk.W)
        
        # 능력치
        stats_frame = ttk.LabelFrame(self.stats_frame, text="능력치", padding="10")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for stat_name in ["힘", "지능", "의지력", "체력", "매력"]:
            stat_frame = ttk.Frame(stats_frame)
            stat_frame.pack(fill=tk.X, pady=2)
            
            label = ttk.Label(stat_frame, text=f"{stat_name}:", width=10)
            label.pack(side=tk.LEFT)
            
            value_label = ttk.Label(stat_frame, text="5")
            value_label.pack(side=tk.LEFT)
            
            self.stats_labels[stat_name] = value_label
        
        self.stat_points_label = ttk.Label(stats_frame, text="사용 가능 포인트: 0", font=('맑은 고딕', 10, 'bold'))
        self.stat_points_label.pack(pady=(10, 0))
        
    def setup_inventory_display(self):
        """인벤토리 디스플레이를 설정합니다."""
        self.inventory_listbox = tk.Listbox(
            self.inventory_frame, 
            bg='#2e2e2e', 
            fg='white', 
            font=('맑은 고딕', 10)
        )
        self.inventory_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def setup_quest_display(self):
        """퀘스트 디스플레이를 설정합니다."""
        self.quest_text = scrolledtext.ScrolledText(
            self.quest_frame, 
            wrap=tk.WORD, 
            height=10,
            font=('맑은 고딕', 10),
            bg='#2e2e2e',
            fg='white'
        )
        self.quest_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def initialize_game(self):
        """게임을 초기화합니다."""
        # API 키 확인
        if not check_api_keys():
            messagebox.showerror("오류", "API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            self.root.destroy()
            sys.exit(1)
        
        # Gemini 클라이언트 초기화
        self.gemini_client = get_gemini_client()
        if not self.gemini_client:
            messagebox.showerror("오류", "Gemini 클라이언트를 초기화할 수 없습니다.")
            self.root.destroy()
            sys.exit(1)
        
        # 대화 히스토리 로드
        if self.game_state.get("history"):
            self.conversation_history = deserialize_history(self.game_state["history"])
        else:
            self.conversation_history = []  # Initialize as empty list; get_gm_response will use INITIAL_HISTORY
        
        # 환영 메시지
        if self.game_state.get("game_turn", 0) == 0:
            welcome_message = """【GM】 인생 RPG의 세계에 오신 것을 환영합니다, 모험가님! 😊
【GM】 저는 당신의 여정을 함께할 게임 마스터입니다.

【GM】 먼저 게임 시스템을 간단히 설명드릴게요:
  ✨ 현실의 과제를 재미있는 퀘스트로 변환합니다
  ✨ 퀘스트 완료 시 XP와 골드를 획득합니다
  ✨ 레벨업하면 능력치 포인트를 얻어 캐릭터를 성장시킬 수 있습니다
  ✨ 특별한 아이템을 획득하면 실제 이미지로 볼 수 있습니다!

【GM】 현재 당신의 기본 능력치는 모두 5로 설정되어 있습니다.

【캐릭터 생성 안내】
원하시면 다음 방법으로 능력치를 커스터마이징할 수 있습니다:
• 오른쪽 '캐릭터 생성' 버튼 클릭 (GUI 방식)
• "/캐릭터생성" 명령어 입력
• 자연어로 직접 설정: "힘 4, 지능 9, 의지력 2, 체력 4, 매력 6으로 설정해줘"

【GM】 능력치 설정을 마치시면, 이번 주에 달성하고 싶은 목표 2-3가지를 알려주세요!

【명령어 안내】
• /스탯 - 현재 상태 확인
• /인벤토리 - 보유 아이템 확인
• /캐릭터생성 - 캐릭터 생성 창 열기
• /도움말 - 전체 도움말 보기
• /종료 - 게임 저장 후 종료"""
            
            self.display_message(welcome_message, "gm")
        
        # UI 업데이트
        self.update_ui()
        
    def send_message(self, event=None):
        """메시지를 전송합니다."""
        user_input = self.input_field.get().strip()
        if not user_input:
            return
        
        self.input_field.delete(0, tk.END)
        self.display_message(f"플레이어: {user_input}", "player")
        
        # 백그라운드 스레드에서 처리
        threading.Thread(target=self.process_message, args=(user_input,), daemon=True).start()
        
    def process_message(self, user_input):
        """메시지를 처리합니다."""
        try:
            # 게임 턴 증가
            self.game_state["game_turn"] = self.game_state.get("game_turn", 0) + 1
            self.player_data["last_activity"] = user_input
            
            # 명령어 처리
            if user_input.lower() == "/종료":
                self.message_queue.put(("【GM】 게임을 저장하고 종료합니다. 다음에 또 만나요!", "gm"))
                self.root.after(1000, self.on_closing)
                return
            
            elif user_input.lower() == "/도움말":
                self.root.after(0, self.show_help)
                return
            
            elif user_input.lower() == "/초기화":
                self.root.after(0, self.confirm_reset)
                return
            
            elif user_input.lower() == "/캐릭터생성":
                self.root.after(0, self.show_character_creation)
                return
            
            # 능력치 분배 처리
            command_result, is_command = process_command(user_input, self.player_data)
            if is_command:
                self.message_queue.put((f"【SYSTEM】 {command_result}", "system"))
                self.root.after(0, self.update_ui)
                return
            elif command_result:  # 명령어였지만 실행되지 않은 경우
                self.message_queue.put((f"【SYSTEM】 {command_result}", "system"))
                return
            
            # 초기 설정 완료 체크
            if not self.player_data.get("initial_setup_done"):
                if any(keyword in user_input for keyword in ["목표", "할 일", "퀘스트", "과제"]):
                    self.player_data["initial_setup_done"] = True
            
            # GM에게 보낼 컨텍스트 구성
            context = self.build_context(user_input)
            
            # GM 응답 받기 - CORRECTED SECTION
            gm_response_text, updated_history = get_gm_response(
                self.gemini_client,      # Use the main gemini client
                context,
                self.conversation_history  # Pass the current conversation history
            )
            self.message_queue.put((gm_response_text, "gm"))
            self.conversation_history = updated_history     # Update the conversation history
            
            # 게임 상태 업데이트 (use gm_response_text)
            updates = parse_gm_response_for_updates(gm_response_text, self.player_data)
            if updates:
                update_msg = "【SYSTEM】 " + ", ".join(updates)
                self.message_queue.put((update_msg, "system"))
                # 퀘스트가 추가되었으면 UI 즉시 업데이트
                if any("퀘스트 추가" in update for update in updates):
                    self.root.after(0, self.update_ui)
            
            # 이미지 생성 확인 (use gm_response_text)
            image_prompt = extract_image_prompt(gm_response_text)
            if image_prompt:
                self.message_queue.put(("【SYSTEM】 아이템 이미지를 생성하는 중...", "system"))
                # Consider running generate_image in a separate thread if it's blocking
                image_path, error = generate_image(image_prompt)
                if image_path:
                    self.image_queue.put(image_path)
                    self.message_queue.put(("【SYSTEM】 아이템 이미지가 생성되었습니다!", "system"))
                else:
                    self.message_queue.put((f"【SYSTEM】 이미지 생성 실패: {error}", "error"))
            
            # 업적 확인
            new_achievements = check_achievements(self.player_data)
            if new_achievements:
                for achievement in new_achievements:
                    self.message_queue.put((f"【SYSTEM】 업적 달성! '{achievement}' 칭호를 획득했습니다!", "system"))
            
            self.root.after(0, self.update_ui)
            
            # 게임 저장 - CORRECTED SECTION
            self.game_state["history"] = self.conversation_history # Save the updated history
            save_game_state(self.game_state)
            
        except Exception as e:
            self.message_queue.put((f"【ERROR】 처리 중 오류 발생: {str(e)}", "error"))
            
    def build_context(self, user_input):
        """GM에게 보낼 컨텍스트를 구성합니다."""
        title = self.player_data.get("title", "")
        
        # 현재 퀘스트 정보 구성
        quest_info = ""
        if self.player_data.get('active_quests'):
            quest_info = "현재 진행 중인 퀘스트:\n"
            for i, quest in enumerate(self.player_data['active_quests'], 1):
                quest_info += f"  {i}. {quest.get('name', '이름 없음')} - {quest.get('status', '진행중')}\n"
                quest_info += f"     설명: {quest.get('description', '설명 없음')}\n"
        else:
            quest_info = "현재 진행 중인 퀘스트: 없음"
        
        return f"""
--- 현재 플레이어 상태 ---
{title}레벨: {self.player_data['level']} (XP: {self.player_data['xp']}/{self.player_data['xp_to_next_level']})
골드: {self.player_data['gold']}G
능력치: 힘 {self.player_data['stats']['힘']}, 지능 {self.player_data['stats']['지능']}, 의지력 {self.player_data['stats']['의지력']}, 체력 {self.player_data['stats']['체력']}, 매력 {self.player_data['stats']['매력']}
보유 스탯 포인트: {self.player_data['stat_points']}
인벤토리: {', '.join(self.player_data['inventory']) if self.player_data['inventory'] else '비어있음'}
업적: {', '.join(self.player_data['achievements']) if self.player_data['achievements'] else '없음'}

{quest_info}

--- 퀘스트 관리 안내 ---
새 퀘스트 추가: [QUEST_ADD: 퀘스트이름 | 설명 | 상태]
퀘스트 완료: [QUEST_COMPLETE: 퀘스트이름]
퀘스트 업데이트: [QUEST_UPDATE: 퀘스트이름 | 새상태 | 새설명]
보상 지급: [REWARD: XP +30, 골드 +15, 아이템: 아이템이름]
---
플레이어: {user_input}
"""
        
    def display_message(self, message, tag="gm"):
        """채팅 디스플레이에 메시지를 추가합니다."""
        self.chat_display.insert(tk.END, message + "\n\n", tag)
        self.chat_display.see(tk.END)
        
    def display_image(self, image_path):
        """이미지를 표시합니다."""
        try:
            img = Image.open(image_path)
            # 이미지 크기 조정
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # 참조 유지
        except Exception as e:
            self.message_queue.put((f"【ERROR】 이미지 표시 오류: {str(e)}", "error"))
            
    def update_ui(self):
        """UI를 업데이트합니다."""
        # 레벨, XP, 골드 업데이트
        title = self.player_data.get("title", "")
        self.level_label.config(text=f"{title}레벨: {self.player_data['level']}")
        self.xp_label.config(text=f"XP: {self.player_data['xp']}/{self.player_data['xp_to_next_level']}")
        self.gold_label.config(text=f"골드: {self.player_data['gold']}G")
        
        # 능력치 업데이트
        for stat_name, label in self.stats_labels.items():
            label.config(text=str(self.player_data['stats'][stat_name]))
        
        self.stat_points_label.config(text=f"사용 가능 포인트: {self.player_data['stat_points']}")
        
        # 인벤토리 업데이트
        self.inventory_listbox.delete(0, tk.END)
        for item in self.player_data['inventory']:
            self.inventory_listbox.insert(tk.END, item)
            
        # 퀘스트 업데이트
        self.quest_text.delete(1.0, tk.END)
        if self.player_data.get('active_quests') and len(self.player_data['active_quests']) > 0:
            self.quest_text.insert(tk.END, "=== 진행 중인 퀘스트 ===\n\n")
            for i, quest in enumerate(self.player_data['active_quests'], 1):
                quest_name = quest.get('name', '이름 없음')
                quest_status = quest.get('status', '진행중')
                self.quest_text.insert(tk.END, f"{i}. {quest_name}\n")
                self.quest_text.insert(tk.END, f"   상태: {quest_status}\n\n")
        else:
            self.quest_text.insert(tk.END, "GM에게 목표를 알려주면 퀘스트로 변환해드립니다!\n\n")
            self.quest_text.insert(tk.END, "예시:\n")
            self.quest_text.insert(tk.END, "• '오늘 운동 30분 하기'\n")
            self.quest_text.insert(tk.END, "• '영어 공부 1시간'\n")
            self.quest_text.insert(tk.END, "• '방 정리하기'\n")
            
    def process_queues(self):
        """큐에 있는 메시지와 이미지를 처리합니다."""
        # 메시지 큐 처리
        try:
            while True:
                message, tag = self.message_queue.get_nowait()
                self.display_message(message, tag)
        except queue.Empty:
            pass
            
        # 이미지 큐 처리
        try:
            while True:
                image_path = self.image_queue.get_nowait()
                self.display_image(image_path)
        except queue.Empty:
            pass
            
        # 100ms 후에 다시 실행
        self.root.after(100, self.process_queues)
        
    def show_character_creation(self):
        """캐릭터 생성 다이얼로그를 표시합니다."""
        def on_character_created(stats):
            if stats:
                # 능력치 적용
                self.player_data["stats"].update(stats)
                self.update_ui()
                
                # 시스템 메시지 표시
                stats_text = ", ".join([f"{stat} {value}" for stat, value in stats.items()])
                self.display_message(f"【SYSTEM】 캐릭터가 생성되었습니다! 능력치: {stats_text}", "system")
                
                # 게임 저장
                save_game_state(self.game_state)
        
        CharacterCreationDialog(self.root, on_character_created)
    
    def show_help(self):
        """도움말을 표시합니다."""
        help_text = """=== 인생 RPG 도움말 ===

【기본 명령어】
• /도움말: 이 도움말을 표시합니다
• /종료: 게임을 저장하고 종료합니다
• /초기화: 게임을 초기화합니다 (주의!)
• /스탯: 현재 캐릭터 상태를 확인합니다
• /인벤토리: 보유 아이템을 확인합니다
• /캐릭터생성: 캐릭터 생성 창을 엽니다

【능력치 관리】
• /능력치분배 [능력치] [포인트]: 스탯 포인트를 분배합니다
  예) /능력치분배 힘 2
• /능력치설정 [능력치:값] [능력치:값] ...: 능력치를 직접 설정합니다
  예) /능력치설정 힘:4 지능:9 의지력:2 체력:4 매력:6
  가능한 능력치: 힘, 지능, 의지력, 체력, 매력

【자연어 능력치 설정】
• 자연어로도 능력치를 설정할 수 있습니다!
  예) "힘 4, 지능 9, 의지력 2, 체력 4, 매력 6으로 설정해줘"
  예) "힘:4 지능:9 의지력:2 체력:4 매력:6"

【게임 진행】
• 일상 과제를 GM에게 알려주면 퀘스트로 변환됩니다
• 퀘스트를 완료하면 XP와 골드를 획득합니다
• 레벨업하면 능력치 포인트 3개를 얻습니다
• 특별한 아이템을 획득하면 이미지로 볼 수 있습니다

【팁】
• 구체적인 목표를 제시하면 더 재미있는 퀘스트가 됩니다
• 정기적으로 진행 상황을 보고하면 더 많은 보상을 받을 수 있습니다
• NPC와 대화하면 특별한 퀘스트를 받을 수 있습니다

【현재 사용 중인 AI 모델】
• Gemini 2.5 Flash (추론 기능 활성화)
• DALL-E 3 (이미지 생성)"""
        
        messagebox.showinfo("도움말", help_text)
        
    def confirm_reset(self):
        """게임 초기화를 확인합니다."""
        if messagebox.askyesno("초기화 확인", "정말로 모든 게임 진행 상황을 초기화하시겠습니까?"):
            self.game_state = copy.deepcopy(DEFAULT_GAME_STATE)
            self.player_data = self.game_state["player_data"]
            self.conversation_history = []  # Reset conversation history
            
            self.chat_display.delete(1.0, tk.END)
            self.display_message("【GM】 게임이 초기화되었습니다. 새로운 모험을 시작해봅시다!", "gm")
            
            self.update_ui()
            save_game_state(self.game_state)
            
    def on_closing(self):
        """프로그램 종료 시 호출됩니다."""
        # Corrected: Save self.conversation_history which is List[Content]
        self.game_state["history"] = self.conversation_history
        save_game_state(self.game_state)
        self.root.destroy()
        
    def run(self):
        """GUI를 실행합니다."""
        self.root.mainloop()