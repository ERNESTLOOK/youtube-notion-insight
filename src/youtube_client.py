from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build


class YouTubeClient:
    def __init__(self, api_key: str):
        self._service = build('youtube', 'v3', developerKey=api_key)

    def resolve_channel_id(self, channel_input: str) -> str | None:
        """@handle 또는 UCxxxxxx 형식 모두 처리해서 채널 ID 반환. 찾지 못하면 None."""
        if channel_input.startswith('UC'):
            return channel_input
        handle = channel_input.lstrip('@')
        response = self._service.channels().list(
            forHandle=handle, part='id'
        ).execute()
        items = response.get('items', [])
        if not items:
            return None
        return items[0]['id']

    def get_recent_videos(self, channel_id: str, hours: int = 24) -> list[dict]:
        """최근 N시간 이내 업로드된 영상 목록 반환"""
        published_after = (
            datetime.now(timezone.utc) - timedelta(hours=hours)
        ).strftime('%Y-%m-%dT%H:%M:%SZ')

        response = self._service.search().list(
            channelId=channel_id,
            part='id,snippet',
            type='video',
            publishedAfter=published_after,
            order='date',
            maxResults=10
        ).execute()

        return [
            {
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            for item in response.get('items', [])
        ]
