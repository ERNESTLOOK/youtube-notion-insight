import os
import time
from dotenv import load_dotenv
from src.youtube_client import YouTubeClient
from src.analyzer import GeminiAnalyzer
from src.notion_manager import NotionManager

load_dotenv()


def run(hours: int = 24):
    yt = YouTubeClient(api_key=os.environ['YOUTUBE_API_KEY'])
    analyzer = GeminiAnalyzer(api_key=os.environ['GEMINI_API_KEY'])
    notion = NotionManager(
        api_key=os.environ['NOTION_API_KEY'],
        channel_db_id=os.environ['NOTION_CHANNEL_DB_ID'],
        insight_db_id=os.environ['NOTION_INSIGHT_DB_ID'],
        trend_parent_id=os.environ['NOTION_TREND_PARENT_ID'],        cloudmap_id=os.environ.get('NOTION_CLOUDMAP_ID', ''),        persons_db_id=os.environ.get('NOTION_PERSONS_DB_ID', ''),        cloudmap_id=os.environ.get('NOTION_CLOUDMAP_ID', ''),
    )

    channels = notion.get_active_channels()
    existing_ids = notion.get_existing_video_ids()
    today_saved = []
    print(f"채널 {len(channels)}개 모니터링 시작 (최근 {hours}시간)")

    for channel in channels:
        channel_id = yt.resolve_channel_id(channel['channel_id'])
        if channel_id is None:
            print(f"  ⚠ 채널 ID 조회 실패: {channel['channel_id']} — 스킵")
            continue

        videos = yt.get_recent_videos(channel_id, hours=hours)
        new_videos = [v for v in videos if v['video_id'] not in existing_ids]
        print(f"[{channel['name']}] 새 영상 {len(new_videos)}개")

        for video in new_videos:
            description = video.get('description', '').strip()
            if not description:
                print(f"  ⏭ 설명 없음: {video['title'][:55]}")
                continue

            print(f"  ✓ 분석 중: {video['title'][:55]}")
            analysis = analyzer.analyze_video(video['title'], description)
            notion.save_insight(video, channel, analysis)                notion.update_persons(analysis.get('persons', []))
            existing_ids.add(video['video_id'])
            today_saved.append({
                'title': video['title'], 'url': video['url'],
                'summary': analysis.get('summary', ''),
                'topic': analysis.get('topic', '기타'),
                'importance': analysis.get('importance', '⭐ 보통'),
            })
            time.sleep(4)  # Gemini 무료 티어 분당 15 요청 제한 대응

        notion.update_channel_last_checked(channel['notion_page_id'])

    # 대시보드 갱신
    dashboard_id = os.environ.get('NOTION_DASHBOARD_ID', '')
    if dashboard_id and today_saved:
        notion.update_dashboard(dashboard_id, today_saved)
        print(f"대시보드 갱신 완료 ({len(today_saved)}개)")

    # 클라우드맵 갱신    all_insights = notion.get_recent_insights(days=30)


if __name__ == '__main__':
    run()
