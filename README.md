# Melody Bridge

Melon → YouTube Music 마이그레이션 CLI.

좋아요 곡, 플레이리스트를 멜론에서 수집해 YouTube Music으로 이전합니다.

저처럼 윈도우에서 멜론 쓰다가 리눅스로 옮기면서 갈아타야하는데 옮길 곡들이 너무 많은 분들은 써보세요.

일단 8000건 정상 마이그레션 진행했습니다.

모자라거나 공식음원 아니라서 못 넣던 곡들 찾으려고 만든게 ytm-collector이니 같이 써도 괜찮을 겁니다.

## 요구사항

- Python 3.10+
- Firefox (music.youtube.com 로그인 필요)

## 설치

```bash
cd melody-bridge
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## 인증

```bash
ytmigrate auth setup    # Firefox 쿠키에서 자동 추출
ytmigrate auth check    # 인증 상태 확인
ytmigrate auth refresh  # 갱신 (401 에러 시)
```

## 사용법

```bash
# 멜론 좋아요 → YTM 좋아요에 추가
ytmigrate likes --member-key <본인_멤버키>

# 멜론 플레이리스트 → YTM 플레이리스트 생성
ytmigrate playlists --member-key <본인_멤버키>

# 멤버키 확인: 멜론 웹 → 내 프로필 → 공유 URL의 memberKey= 값
```

## 구조

```
src/ytmigrate/
├── cli.py        # Typer CLI
├── auth.py       # Firefox 쿠키 → YTM 인증
├── melon.py      # 멜론 스크래핑
├── matcher.py    # 곡명 매칭 (Melon ↔ YTM)
└── ...
```

## 테스트

```bash
pytest tests/ -v
```

## 라이선스

MIT
