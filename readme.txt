# 인생 RPG - Life is Game

현실의 일상과 목표를 재미있는 RPG 게임으로 만들어주는 개인용 프로그램입니다.

## 🎮 주요 기능

### 핵심 시스템
- **퀘스트 시스템**: 현실 과제를 창의적인 퀘스트로 변환
- **레벨링**: XP 획득으로 캐릭터 성장
- **능력치**: 힘, 지능, 의지력, 체력, 매력 5가지 스탯
- **아이템 시스템**: 퀘스트 완료 시 랜덤 아이템 드랍
- **이미지 생성**: 특별한 아이템을 실제 이미지로 생성

### 확장 기능
- **돌발 퀘스트**: 진행 중인 과제에 맞는 소규모 미션
- **NPC 시스템**: 힐러 엘라, 대장장이 볼드, 지혜의 올빼미
- **전직 시스템**: 레벨 5, 10에서 직업 선택
- **업적 시스템**: 다양한 도전 과제와 칭호
- **메인 스토리**: 장기 목표를 스토리로 구성

## 🚀 설치 및 실행

### 1. 필요한 라이브러리 설치
```bash
pip install -r requirements.txt
```

**참고**: 기존 `google-generativeai` 라이브러리를 사용 중이었다면 제거하고 새로운 SDK를 설치하세요:
```bash
pip uninstall google-generativeai
pip install google-genai
```

### 2. API 키 설정
1. `.env.template`를 `.env`로 복사
2. 다음 API 키들을 발급받아 `.env` 파일에 입력:

#### Gemini API Key 발급
1. [Google AI Studio](https://aistudio.google.com/) 접속
2. 계정 로그인 후 API 키 생성
3. 생성된 키를 `GEMINI_API_KEY`에 입력

#### OpenAI API Key 발급
1. [OpenAI Platform](https://platform.openai.com/api-keys) 접속
2. 계정 로그인 후 API 키 생성
3. 생성된 키를 `OPENAI_API_KEY`에 입력

### 3. 프로그램 실행
```bash
python main.py
```

## 🎯 사용 방법

### 게임 시작
1. 프로그램 실행 후 GM이 환영 인사를 합니다
2. 이번 주의 목표 2-3가지를 입력하세요
3. GM이 자동으로 퀘스트로 변환해드립니다

### 기본 명령어
- `/스탯` - 현재 캐릭터 상태 확인
- `/인벤토리` - 보유 아이템 확인
- `/능력치분배 힘 2` - 능력치 포인트 분배
- `/도움말` - 전체 도움말 보기
- `/종료` - 게임 저장 후 종료

### 게임 진행 팁
- 구체적인 목표를 제시하면 더 흥미로운 퀘스트가 생성됩니다
- 퀘스트 완료를 보고하면 XP와 골드를 획득합니다
- 레벨업 시 능력치 포인트를 분배하여 캐릭터를 성장시키세요

### 기술 스택

### AI 모델
- **Gemini 2.5 Flash**: 게임 마스터 역할 (새로운 Google Gen AI SDK 사용)
- **GPT-Image-1**: 최신 멀티모달 이미지 생성 (GPT-4o 기반)

### 프로그래밍
- **Python 3.8+**: 메인 언어
- **Google Gen AI SDK**: 최신 통합 Gemini SDK
- **Tkinter**: GUI 프레임워크
- **PIL (Pillow)**: 이미지 처리
- **Requests**: HTTP 통신

## 📁 파일 구조

```
lifeisgame/
├── main.py                 # 메인 실행 파일
├── config.py              # 설정 관리
├── game_state_manager.py  # 게임 상태 저장/로드
├── gemini_client.py       # Gemini API 클라이언트
├── openai_image_client.py # OpenAI 이미지 생성
├── game_logic.py          # 게임 로직 처리
├── rpg_gui.py            # GUI 메인 클래스
├── requirements.txt       # 필요 라이브러리
├── .env.template         # 환경변수 템플릿
├── game_data.json        # 게임 진행 상황 (자동 생성)
└── cached_images/        # 생성된 이미지 캐시 (자동 생성)
```

## 🎨 게임 예시

### 퀘스트 예시
```
플레이어: "오늘 운동 30분 하기"
GM: "'나태의 그림자 정령(Lv3)' 등장! 30분간의 육체 단련으로 물리치세요!
     보상: XP +25, 골드 +12, 아이템 드랍 확률 60%"

완료 후:
GM: "【SYSTEM】 전투 승리! XP +25, 골드 +12
     [희귀✨] '강철 의지의 팔찌' 드랍! 
     (이미지 생성: 강철 의지의 팔찌, 게임 아이템 카드 스타일, 판타지풍, 빛나는 효과)"
```

## ⚠️ 주의사항

### API 사용량
- Gemini 2.5 Flash: 추론 토큰 사용으로 비용 발생 가능
- GPT-Image-1: 이미지 생성당 약 $0.02-$0.19 비용 (품질에 따라)
- 적절한 사용량 관리를 권장합니다

### 데이터 저장
- 게임 진행 상황은 `game_data.json`에 자동 저장됩니다
- 생성된 이미지는 `cached_images/` 폴더에 캐시됩니다
- 백업을 원할 경우 해당 파일들을 복사해두세요

## 🔧 설정 변경

### Thinking Budget 조정
`config.py`에서 `GEMINI_THINKING_CONFIG`의 `thinking_budget` 값을 조정할 수 있습니다:
- `0`: 추론 비활성화 (속도 우선)
- `1024`: 기본값 (균형)
- `24576`: 최대값 (품질 우선)

### 이미지 생성 비활성화
비용 절약을 위해 이미지 생성을 비활성화하려면 `.env`에서 `OPENAI_API_KEY`를 제거하세요.

## 🐛 문제 해결

### 일반적인 오류
1. **API 키 오류**: `.env` 파일의 API 키가 올바른지 확인
2. **라이브러리 오류**: `pip install -r requirements.txt` 재실행
3. **이미지 표시 오류**: Pillow 라이브러리 버전 확인

### 성능 최적화
- 오래된 캐시 이미지 주기적 삭제
- `game_data.json` 파일이 너무 클 경우 백업 후 초기화

## 📄 라이선스

개인 사용 목적으로 자유롭게 사용 가능합니다.
API 사용에 따른 비용은 사용자 부담입니다.

---

**즐거운 인생 RPG 되세요! 🎮✨**