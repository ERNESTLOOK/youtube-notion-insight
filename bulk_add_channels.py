"""
채널 일괄 등록 스크립트
channel_guide.md 의 주요 채널을 Notion 채널 목록 DB에 한 번에 추가합니다.

실행:
    python bulk_add_channels.py

동작:
    1. YouTube API로 핸들(@xxx)을 채널 ID(UCxxx)로 변환
    2. 이미 Notion에 등록된 채널은 건너뜀 (중복 방지)
    3. 신규 채널만 Notion DB에 추가
"""

import os
from dotenv import load_dotenv
from src.youtube_client import YouTubeClient
from src.notion_manager import NotionManager

load_dotenv()

# ─── 등록할 채널 목록 ─────────────────────────────────────────────────────────
# handle: YouTube @핸들 (또는 UCxxx 채널 ID 직접 입력 가능)
# tags:   Notion 다중 선택 태그 (분야/태그 컬럼)
CHANNELS = [
    # ── 해외 유튜브 (글로벌 트렌드) ───────────────────────────────────────────
    {
        "name": "AI Explained",
        "handle": "@aiexplained-official",
        "tags": ["AI 트렌드", "LLM", "규제"],
    },
    {
        "name": "Matthew Berman",
        "handle": "@matthew_berman",
        "tags": ["AI 도구", "오픈소스", "생성형AI"],
    },
    {
        "name": "Matt Wolfe",
        "handle": "@mreflow",
        "tags": ["AI 뉴스", "비즈니스", "툴 큐레이션"],
    },
    {
        "name": "DeepLearning.AI",
        "handle": "@deeplearningai",
        "tags": ["AI 교육", "LLM", "기초"],
    },
    {
        "name": "The AI Grid",
        "handle": "@TheAiGrid",
        "tags": ["AI 도구", "에이전트", "자동화"],
    },
    {
        "name": "Tech With Tim",
        "handle": "@TechWithTim",
        "tags": ["AI 교육", "파이썬", "실습"],
    },
    {
        "name": "Two Minute Papers",
        "handle": "@TwoMinutePapers",
        "tags": ["AI 논문", "연구", "컴퓨터 비전"],
    },
    {
        "name": "Fireship",
        "handle": "@Fireship",
        "tags": ["AI 뉴스", "개발 트렌드"],
    },
    # ── 해외 팟캐스트 (YouTube 채널 보유) ────────────────────────────────────
    {
        "name": "Lex Fridman",
        "handle": "@lexfridman",
        "tags": ["AI 인터뷰", "철학", "기술 정책"],
    },
    {
        "name": "Dwarkesh Patel",
        "handle": "@DwarkeshPatel",
        "tags": ["AGI", "스케일링", "지정학"],
    },
    {
        "name": "Latent Space",
        "handle": "@latentspacepod",
        "tags": ["AI 엔지니어링", "에이전트", "MLOps"],
    },
    {
        "name": "TWIML AI",
        "handle": "@twimlai",
        "tags": ["ML 연구", "엔터프라이즈 AI"],
    },
    {
        "name": "a16z",
        "handle": "@a16z",
        "tags": ["AI 투자", "스타트업", "인프라"],
    },
    {
        "name": "No Priors",
        "handle": "@NoPriorsPod",
        "tags": ["AI 제품", "스타트업", "VC"],
    },
    {
        "name": "OpenAI",
        "handle": "@OpenAI",
        "tags": ["GPT", "생성형AI", "정책"],
    },
    # ── 한국어 채널 ───────────────────────────────────────────────────────────
    {
        "name": "조코딩",
        "handle": "@jocoding",
        "tags": ["AI 도구", "개발 실무", "국내 트렌드"],
    },
    {
        "name": "Google Cloud APAC (AI Breakfast)",
        "handle": "@GoogleCloudAPAC",
        "tags": ["AI 클라우드", "국내 사례", "구글"],
    },
]
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    yt = YouTubeClient(api_key=os.environ["YOUTUBE_API_KEY"])
    notion = NotionManager(
        api_key=os.environ["NOTION_API_KEY"],
        channel_db_id=os.environ["NOTION_CHANNEL_DB_ID"],
        insight_db_id=os.environ["NOTION_INSIGHT_DB_ID"],
        trend_parent_id=os.environ["NOTION_TREND_PARENT_ID"],
    )

    # 이미 등록된 채널 ID 목록 조회 (중복 방지)
    print("📋 Notion에서 기존 채널 목록 조회 중...")
    existing = notion.get_all_channel_ids()
    print(f"   현재 등록된 채널: {len(existing)}개\n")

    success, skipped, failed = [], [], []

    for ch in CHANNELS:
        name = ch["name"]
        handle = ch["handle"]

        # 채널 ID 조회
        channel_id = yt.resolve_channel_id(handle)
        if not channel_id:
            print(f"  ✗ [{name}] 채널 ID 조회 실패 — 핸들 확인 필요: {handle}")
            failed.append(name)
            continue

        # 중복 확인
        if channel_id in existing:
            print(f"  ↩ [{name}] 이미 등록됨 — 건너뜀 ({channel_id})")
            skipped.append(name)
            continue

        # Notion에 추가
        notion.add_channel({
            "name": name,
            "channel_id": channel_id,
            "tags": ch["tags"],
        })
        print(f"  ✓ [{name}] 추가 완료 ({channel_id})")
        success.append(name)

    # 결과 요약
    print(f"""
────────────────────────────────
결과 요약
  ✓ 추가됨:   {len(success)}개  {success}
  ↩ 건너뜀:   {len(skipped)}개  {skipped}
  ✗ 실패:     {len(failed)}개  {failed}
────────────────────────────────
""")


if __name__ == "__main__":
    main()
