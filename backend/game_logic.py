# game_logic.py
import re
import random

def parse_gm_response_for_updates(response_text, player_data, game_state):
    """GM 응답에서 Gemini 태그 기반으로 게임 상태 변경 사항을 파싱합니다."""
    # player_data is game_state["player_data"]
    # game_state is available if other parts of it are needed in the future.
    updates = []
    
    print(f"[DEBUG] Gemini 태그 파싱 시작...")
    
    # 1. 퀘스트 추가 파싱: [QUEST_ADD: 이름 | 설명 | 상태]
    quest_add_matches = re.findall(r'\[QUEST_ADD:\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^\]]+)\]', response_text)
    for quest_name, description, status in quest_add_matches:
        quest_name = quest_name.strip()
        description = description.strip()
        status = status.strip()
        
        # 기존 퀘스트 중복 확인
        existing_quest_names = [q.get("name", "") for q in player_data.get("active_quests", [])]
        if quest_name not in existing_quest_names:
            new_quest = {
                "name": quest_name,
                "description": description,
                "status": status
            }
            if "active_quests" not in player_data:
                player_data["active_quests"] = []
            player_data["active_quests"].append(new_quest)
            updates.append(f"새 퀘스트 추가: {quest_name}")
            print(f"[DEBUG] 퀘스트 추가됨: {quest_name} - {description}")
    
    # 2. 퀘스트 완료 파싱: [QUEST_COMPLETE: 이름]
    quest_complete_matches = re.findall(r'\[QUEST_COMPLETE:\s*([^\]]+)\]', response_text)
    for quest_name in quest_complete_matches:
        quest_name = quest_name.strip()
        
        # 해당 퀘스트를 완료 상태로 변경하거나 제거
        if "active_quests" in player_data:
            for quest in player_data["active_quests"]:
                if quest.get("name") == quest_name:
                    quest["status"] = "완료"
                    updates.append(f"퀘스트 완료: {quest_name}")
                    print(f"[DEBUG] 퀘스트 완료됨: {quest_name}")
                    break
    
    # 3. 퀘스트 업데이트 파싱: [QUEST_UPDATE: 이름 | 새상태 | 새설명]
    quest_update_matches = re.findall(r'\[QUEST_UPDATE:\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^\]]+)\]', response_text)
    for quest_name, new_status, new_description in quest_update_matches:
        quest_name = quest_name.strip()
        new_status = new_status.strip()
        new_description = new_description.strip()
        
        if "active_quests" in player_data:
            for quest in player_data["active_quests"]:
                if quest.get("name") == quest_name:
                    quest["status"] = new_status
                    quest["description"] = new_description
                    updates.append(f"퀘스트 업데이트: {quest_name}")
                    print(f"[DEBUG] 퀘스트 업데이트됨: {quest_name} - {new_status}")
                    break
    
    # 4. 보상 파싱: [REWARD: XP +30, 골드 +15, 아이템: 지식의 파편]
    reward_matches = re.findall(r'\[REWARD:\s*([^\]]+)\]', response_text)
    for reward_text in reward_matches:
        # XP 파싱
        xp_matches = re.findall(r'XP\s*\+\s*(\d+)', reward_text, re.IGNORECASE)
        for xp_match in xp_matches:
            new_xp = int(xp_match)
            player_data["xp"] += new_xp
            updates.append(f"XP +{new_xp}")
        
        # 골드 파싱
        gold_matches = re.findall(r'골드\s*\+\s*(\d+)', reward_text, re.IGNORECASE)
        for gold_match in gold_matches:
            new_gold = int(gold_match)
            player_data["gold"] += new_gold
            updates.append(f"골드 +{new_gold}")
        
        # 아이템 파싱
        item_matches = re.findall(r'아이템:\s*([^,\]]+)', reward_text)
        for item_name in item_matches:
            item_name = item_name.strip()
            if item_name and item_name not in player_data["inventory"]:
                player_data["inventory"].append(item_name)
                updates.append(f"아이템 획득: {item_name}")
        
        print(f"[DEBUG] 보상 처리됨: {reward_text}")
    
    # 5. 기존 XP/골드 파싱도 유지 (Gemini가 태그를 안 쓸 수도 있으니)
    xp_matches = re.findall(r"XP\s*\+\s*(\d+)", response_text, re.IGNORECASE)
    for xp_match in xp_matches:
        new_xp = int(xp_match)
        player_data["xp"] += new_xp
        updates.append(f"XP +{new_xp}")
    
    gold_matches = re.findall(r"(?:골드|G)\s*\+\s*(\d+)", response_text, re.IGNORECASE)
    for gold_match in gold_matches:
        new_gold = int(gold_match)
        player_data["gold"] += new_gold
        updates.append(f"골드 +{new_gold}")
    
    print(f"[DEBUG] 태그 파싱 완료. 총 활성 퀘스트: {len(player_data.get('active_quests', []))}")
    
    # 레벨업 처리
    leveled_up = False
    while player_data["xp"] >= player_data["xp_to_next_level"]:
        leveled_up = True
        player_data["level"] += 1
        player_data["xp"] -= player_data["xp_to_next_level"]
        player_data["xp_to_next_level"] = int(player_data["xp_to_next_level"] * 1.5)
        player_data["stat_points"] += 3
    
    if leveled_up:
        updates.append(f"레벨업! Lv.{player_data['level']} 달성! 능력치 포인트 +3")
    
    return updates

def extract_image_prompt(gm_text):
    """GM 응답에서 이미지 생성 프롬프트를 추출합니다."""
    # 여러 패턴으로 이미지 생성 요청을 찾음
    patterns = [
        r"\(이미지\s*생성:\s*([^)]+)\)",
        r"이미지\s*생성:\s*([^\n\r]+)",
        r"\[이미지:\s*([^\]]+)\]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, gm_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def parse_natural_language_stats(user_input):
    """자연어에서 능력치 설정을 파싱합니다."""
    # 능력치 패턴 매칭
    stat_patterns = {
        "힘": [r"힘\s*[:=]?\s*(\d+)", r"str\s*[:=]?\s*(\d+)", r"strength\s*[:=]?\s*(\d+)"],
        "지능": [r"지능\s*[:=]?\s*(\d+)", r"int\s*[:=]?\s*(\d+)", r"intelligence\s*[:=]?\s*(\d+)"],
        "의지력": [r"의지력\s*[:=]?\s*(\d+)", r"will\s*[:=]?\s*(\d+)", r"willpower\s*[:=]?\s*(\d+)"],
        "체력": [r"체력\s*[:=]?\s*(\d+)", r"hp\s*[:=]?\s*(\d+)", r"health\s*[:=]?\s*(\d+)"],
        "매력": [r"매력\s*[:=]?\s*(\d+)", r"cha\s*[:=]?\s*(\d+)", r"charisma\s*[:=]?\s*(\d+)"]
    }
    
    found_stats = {}
    text = user_input.lower()
    
    for stat_name, patterns in stat_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                found_stats[stat_name] = int(match.group(1))
                break
    
    return found_stats

def process_command(user_input, player_data, game_state):
    """사용자 명령어를 처리합니다."""
    # player_data is game_state["player_data"]
    # game_state is available if other parts of it are needed in the future.
    command = user_input.lower().strip()
    
    # 자연어 능력치 설정 감지
    natural_stats = parse_natural_language_stats(user_input)
    if len(natural_stats) >= 3 and not command.startswith("/"):  # 3개 이상의 능력치가 감지되고 명령어가 아닌 경우
        total_points = sum(natural_stats.values())
        if len(natural_stats) == 5 and total_points == 25:
            player_data["stats"].update(natural_stats)
            result = "자연어로 능력치가 설정되었습니다:\n"
            for stat, value in natural_stats.items():
                result += f"• {stat}: {value}\n"
            return result.strip(), True
        elif len(natural_stats) == 5:
            return f"능력치 총합이 25가 되어야 합니다. (현재 총합: {total_points})", False
        else:
            missing_stats = set(["힘", "지능", "의지력", "체력", "매력"]) - set(natural_stats.keys())
            return f"모든 능력치를 설정해주세요. 누락된 능력치: {', '.join(missing_stats)}", False
    
    if command.startswith("/능력치분배"):
        try:
            parts = user_input.split()
            if len(parts) < 3:
                return "사용법: /능력치분배 [능력치] [포인트]", False
            
            stat_name = parts[1]
            points = int(parts[2])
            
            # 능력치 이름 정규화
            stat_map = {
                "힘": "힘", "str": "힘", "strength": "힘",
                "지능": "지능", "int": "지능", "intelligence": "지능",
                "의지력": "의지력", "will": "의지력", "willpower": "의지력",
                "체력": "체력", "hp": "체력", "health": "체력",
                "매력": "매력", "cha": "매력", "charisma": "매력"
            }
            
            normalized_stat = stat_map.get(stat_name.lower())
            if not normalized_stat:
                return f"유효하지 않은 능력치입니다. 가능한 능력치: {', '.join(player_data['stats'].keys())}", False
            
            if points <= 0 or points > player_data["stat_points"]:
                return f"1에서 {player_data['stat_points']} 사이의 포인트를 분배할 수 있습니다.", False
            
            player_data["stats"][normalized_stat] += points
            player_data["stat_points"] -= points
            return f"{normalized_stat} +{points} (현재: {player_data['stats'][normalized_stat]})", True
        except ValueError:
            return "포인트는 숫자로 입력해주세요.", False
        except Exception as e:
            return f"능력치 분배 중 오류가 발생했습니다: {str(e)}", False
    
    elif command.startswith("/상점"):
        return "상점 기능은 아직 구현 중입니다.", False
    
    elif command.startswith("/인벤토리"):
        if player_data["inventory"]:
            inventory_list = "\n".join([f"• {item}" for item in player_data["inventory"]])
            return f"보유 아이템:\n{inventory_list}", False
        else:
            return "인벤토리가 비어있습니다.", False
    
    elif command.startswith("/능력치설정"):
        try:
            # 사용법: /능력치설정 힘:4 지능:9 의지력:2 체력:4 매력:6
            parts = user_input.split()[1:]  # 첫 번째 부분(명령어) 제외
            if not parts:
                return "사용법: /능력치설정 힘:값 지능:값 의지력:값 체력:값 매력:값", False
            
            stat_updates = {}
            total_points = 0
            
            for part in parts:
                if ':' in part:
                    stat_name, value = part.split(':', 1)
                    stat_name = stat_name.strip()
                    value = int(value.strip())
                    
                    # 능력치 이름 정규화
                    stat_map = {
                        "힘": "힘", "str": "힘", "strength": "힘",
                        "지능": "지능", "int": "지능", "intelligence": "지능",
                        "의지력": "의지력", "will": "의지력", "willpower": "의지력",
                        "체력": "체력", "hp": "체력", "health": "체력",
                        "매력": "매력", "cha": "매력", "charisma": "매력"
                    }
                    
                    normalized_stat = stat_map.get(stat_name.lower())
                    if normalized_stat:
                        stat_updates[normalized_stat] = value
                        total_points += value
            
            if len(stat_updates) == 5 and total_points == 25:  # 총 25포인트로 제한
                player_data["stats"].update(stat_updates)
                result = "능력치가 설정되었습니다:\n"
                for stat, value in stat_updates.items():
                    result += f"• {stat}: {value}\n"
                return result.strip(), True
            else:
                return f"모든 능력치를 설정하고 총합이 25가 되어야 합니다. (현재 총합: {total_points})", False
                
        except ValueError:
            return "능력치 값은 숫자로 입력해주세요.", False
        except Exception as e:
            return f"능력치 설정 중 오류가 발생했습니다: {str(e)}", False
    
    elif command.startswith("/스탯"):
        stats_text = f"""
현재 캐릭터 정보:
레벨: {player_data['level']} (XP: {player_data['xp']}/{player_data['xp_to_next_level']})
골드: {player_data['gold']}G
사용 가능 스탯 포인트: {player_data['stat_points']}

능력치:
• 힘: {player_data['stats']['힘']}
• 지능: {player_data['stats']['지능']}
• 의지력: {player_data['stats']['의지력']}
• 체력: {player_data['stats']['체력']}
• 매력: {player_data['stats']['매력']}
"""
        return stats_text.strip(), False
    
    return None, False

def generate_random_quest(difficulty="normal"):
    """랜덤 퀘스트를 생성합니다."""
    quest_templates = {
        "easy": [
            {"name": "5분 정리", "xp": 10, "gold": 5, "description": "주변 5분 정리하기"},
            {"name": "물 한 잔", "xp": 5, "gold": 2, "description": "물 한 잔 마시기"},
            {"name": "깊은 호흡", "xp": 8, "gold": 3, "description": "1분간 깊은 호흡하기"}
        ],
        "normal": [
            {"name": "30분 집중", "xp": 25, "gold": 10, "description": "30분간 집중해서 작업하기"},
            {"name": "운동 15분", "xp": 20, "gold": 8, "description": "15분 간단한 운동하기"},
            {"name": "독서 20분", "xp": 22, "gold": 9, "description": "20분간 책 읽기"}
        ],
        "hard": [
            {"name": "1시간 몰입", "xp": 50, "gold": 25, "description": "1시간 완전 몰입 작업"},
            {"name": "운동 45분", "xp": 45, "gold": 20, "description": "45분 본격적인 운동"},
            {"name": "새로운 기술 학습", "xp": 60, "gold": 30, "description": "새로운 기술이나 지식 학습"}
        ]
    }
    
    quests = quest_templates.get(difficulty, quest_templates["normal"])
    return random.choice(quests)

def check_achievements(player_data, game_state):
    """업적 달성 여부를 확인합니다."""
    # player_data is game_state["player_data"]
    # game_state is available if other parts of it are needed in the future.
    new_achievements = []
    
    # 레벨 기반 업적
    if player_data["level"] >= 5 and "초보 모험가" not in player_data["achievements"]:
        player_data["achievements"].append("초보 모험가")
        player_data["title"] = "[초보 모험가] "
        new_achievements.append("초보 모험가")
    
    if player_data["level"] >= 10 and "숙련된 모험가" not in player_data["achievements"]:
        player_data["achievements"].append("숙련된 모험가")
        player_data["title"] = "[숙련된 모험가] "
        new_achievements.append("숙련된 모험가")
    
    # 골드 기반 업적
    if player_data["gold"] >= 100 and "부자" not in player_data["achievements"]:
        player_data["achievements"].append("부자")
        new_achievements.append("부자")
    
    # 인벤토리 기반 업적
    if len(player_data["inventory"]) >= 10 and "수집가" not in player_data["achievements"]:
        player_data["achievements"].append("수집가")
        new_achievements.append("수집가")
    
    return new_achievements

def calculate_quest_reward(difficulty, player_level):
    """퀘스트 난이도와 플레이어 레벨에 따른 보상을 계산합니다."""
    base_rewards = {
        "easy": {"xp": 10, "gold": 5},
        "normal": {"xp": 25, "gold": 12},
        "hard": {"xp": 50, "gold": 25},
        "expert": {"xp": 100, "gold": 50}
    }
    
    base = base_rewards.get(difficulty, base_rewards["normal"])
    level_multiplier = 1 + (player_level - 1) * 0.1  # 레벨당 10% 증가
    
    return {
        "xp": int(base["xp"] * level_multiplier),
        "gold": int(base["gold"] * level_multiplier)
    }