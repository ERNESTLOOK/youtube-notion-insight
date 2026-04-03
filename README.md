# YouTube → Notion 인사이트 대시보드

전문 분야 유튜브 채널을 모니터링하고, 새 영상의 핵심 인사이트를 노션에 자동 축적합니다.

## 동작 방식

- **매일 오전 8시 (KST):** GitHub Actions가 등록된 채널의 새 영상을 감지 → 자막 추출 → Gemini 분석 → 노션 저장
- **매주 월요일 오전 9시 (KST):** 지난 7일 인사이트를 집계해 주간 트렌드 페이지 자동 생성

## 설정 순서

### 1. 노션 설정

노션에 아래 두 개의 데이터베이스를 생성합니다.

**채널 목록 DB (Channels)**

| 속성명 | 타입 |
|--------|------|
| 채널명 | 제목 |
| 채널 ID | 텍스트 |
| 분야/태그 | 다중 선택 |
| 활성화 | 체크박스 |
| 마지막 체크 | 날짜 |

**영상 인사이트 DB (Video Insights)**

| 속성명 | 타입 |
|--------|------|
| 영상 제목 | 제목 |
| 채널명 | 관계형 (채널 목록 DB 연결) |
| 분야 | 다중 선택 |
| 업로드 날짜 | 날짜 |
| 트렌드 키워드 | 다중 선택 |
| 한줄 요약 | 텍스트 |
| 원본 링크 | URL |
| 영상 ID | 텍스트 |

주간 트렌드 페이지가 생성될 부모 페이지도 별도로 만들어 두세요.

### 2. API 키 발급

| 키 | 발급 위치 |
|----|-----------|
| Notion API Key | notion.so/my-integrations |
| YouTube API Key | Google Cloud Console → YouTube Data API v3 |
| Gemini API Key | aistudio.google.com |

### 3. GitHub 저장소 설정

```bash
git remote add origin https://github.com/<사용자명>/youtube-notion-insight.git
git push -u origin main
```

GitHub 저장소 → Settings → Secrets and variables → Actions에서 아래 Secrets 등록:

- `NOTION_API_KEY`
- `NOTION_CHANNEL_DB_ID` (DB URL의 32자리 ID)
- `NOTION_INSIGHT_DB_ID`
- `NOTION_TREND_PARENT_ID` (주간 트렌드 부모 페이지 ID)
- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY`

### 4. 채널 등록

**AI 추천으로 등록:**
```bash
cp .env.example .env  # API 키 입력 후
python channel_discover.py
```

**노션에서 직접 추가:** 채널 목록 DB에 행 추가 후 활성화 체크박스 체크

## 수동 실행

```bash
# 오늘 새 영상 즉시 분석
python -m src.daily_check

# 주간 트렌드 즉시 생성
python -m src.weekly_trend
```

GitHub Actions 탭에서 `workflow_dispatch`로 수동 실행도 가능합니다.

## 테스트

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
