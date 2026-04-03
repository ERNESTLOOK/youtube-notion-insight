import os
from collections import Counter
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.analyzer import GeminiAnalyzer
from src.notion_manager import NotionManager

load_dotenv()


def run():
    analyzer = GeminiAnalyzer(api_key=os.environ['GEMINI_API_KEY'])
    notion = NotionManager(
        api_key=os.environ['NOTION_API_KEY'],
        channel_db_id=os.environ['NOTION_CHANNEL_DB_ID'],
        insight_db_id=os.environ['NOTION_INSIGHT_DB_ID'],
        trend_parent_id=os.environ['NOTION_TREND_PARENT_ID'],
    )

    insights = notion.get_recent_insights(days=7)
    print(f"지난 7일 영상 {len(insights)}개 집계 중")

    if not insights:
        print("집계할 영상 없음. 종료")
        return

    keyword_counter = Counter()
    for item in insights:
        keyword_counter.update(item['keywords'])
    top_keywords = [kw for kw, _ in keyword_counter.most_common(10)]

    top_videos = insights[:3]
    trend_text = analyzer.analyze_weekly_trend(insights)
    week_label = datetime.now(timezone.utc).strftime('%Y-W%U')

    notion.create_weekly_trend_page(week_label, trend_text, top_keywords, top_videos)
    print(f"주간 트렌드 페이지 생성 완료: {week_label}")


if __name__ == '__main__':
    run()
