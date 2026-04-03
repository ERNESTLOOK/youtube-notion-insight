import os
from dotenv import load_dotenv
from src.analyzer import GeminiAnalyzer
from src.notion_manager import NotionManager

load_dotenv()


def main():
    domain = input("채널을 찾을 분야를 입력하세요 (예: AI 교육, 마케팅): ").strip()
    if not domain:
        print("분야를 입력해야 합니다.")
        return

    analyzer = GeminiAnalyzer(api_key=os.environ['GEMINI_API_KEY'])
    notion = NotionManager(
        api_key=os.environ['NOTION_API_KEY'],
        channel_db_id=os.environ['NOTION_CHANNEL_DB_ID'],
        insight_db_id=os.environ['NOTION_INSIGHT_DB_ID'],
        trend_parent_id=os.environ['NOTION_TREND_PARENT_ID'],
    )

    print(f"\n'{domain}' 분야 인기 채널 검색 중...")
    channels = analyzer.suggest_channels(domain)

    print(f"\n추천 채널 {len(channels)}개:")
    for i, ch in enumerate(channels, 1):
        tags = ', '.join(ch['tags'])
        print(f"  {i}. {ch['name']} ({ch['channel_id']}) [{tags}]")

    answer = input("\n모두 노션에 추가할까요? (y/N): ").strip().lower()
    if answer != 'y':
        print("취소되었습니다.")
        return

    for ch in channels:
        notion.add_channel(ch)
        print(f"  ✓ 추가됨: {ch['name']}")

    print("\n완료! 노션 채널 목록 DB를 확인하세요.")


if __name__ == '__main__':
    main()
