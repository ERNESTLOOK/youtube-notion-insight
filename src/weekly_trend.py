import os
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

    print("Gemini로 주간 리포트 생성 중...")
    report = analyzer.generate_weekly_report(insights)

    week_label = datetime.now(timezone.utc).strftime('%Y년 %m월 %d일 주차')
    notion.create_weekly_report_page(week_label, report, insights)
    print(f"주간 리포트 생성 완료: {week_label}")
    print(f"헤드라인: {report.get('headline', '')}")


if __name__ == '__main__':
    run()
