import os
import time
from dotenv import load_dotenv
from src.youtube_client import YouTubeClient
from src.transcript import get_transcript
from src.analyzer import GeminiAnalyzer
from src.notion_manager import NotionManager

load_dotenv()


def run():
    yt = YouTubeClient(api_key=os.environ['YOUTUBE_API_KEY'])
    analyzer = GeminiAnalyzer(api_key=os.environ['GEMINI_API_KEY'])
    notion = NotionManager(
        api_key=os.environ['NOTION_API_KEY'],
        channel_db_id=os.environ['NOTION_CHANNEL_DB_ID'],
        insight_db_id=os.environ['NOTION_INSIGHT_DB_ID'],
        trend_parent_id=os.environ['NOTION_TREND_PARENT_ID'],
    )

    channels = notion.get_active_channels()
    existing_ids = notion.get_existing_video_ids()
    print(f"채널 {len(channels)}개 모니터링 시작")

    for channel in channels:
        channel_id = yt.resolve_channel_id(channel['channel_id'])
        videos = yt.get_recent_videos(channel_id, hours=24)
        new_videos = [v for v in videos if v['video_id'] not in existing_ids]
        print(f"[{channel['name']}] 새 영상 {len(new_videos)}개")

        for video in new_videos:
            transcript = get_transcript(video['video_id'])
            if transcript is None:
                print(f"  ⏭ 자막 없음: {video['title']}")
                continue

            print(f"  ✓ 분석 중: {video['title']}")
            analysis = analyzer.analyze_transcript(transcript, video['title'])
            notion.save_insight(video, channel, analysis)
            existing_ids.add(video['video_id'])
            time.sleep(4)  # Gemini 무료 티어 분당 15 요청 제한 대응

        notion.update_channel_last_checked(channel['notion_page_id'])

    print("완료")


if __name__ == '__main__':
    run()
