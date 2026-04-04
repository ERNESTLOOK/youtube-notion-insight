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
        """최근 N시간 이내 업로드된 영상 목록 반환.

        채널 업로드 플레이리스트를 직접 조회해 누락 없이 가져옵니다.
        search() 대비 quota 비용이 낮고 인덱싱 지연 영향을 받지 않습니다.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # 채널의 업로드 플레이리스트 ID 조회 (UC → UU 치환)
        uploads_playlist_id = 'UU' + channel_id[2:]

        video_ids = []
        next_page_token = None

        while True:
            kwargs = {
                'playlistId': uploads_playlist_id,
                'part': 'snippet',
                'maxResults': 50,
            }
            if next_page_token:
                kwargs['pageToken'] = next_page_token

            response = self._service.playlistItems().list(**kwargs).execute()
            items = response.get('items', [])

            stop = False
            for item in items:
                published_at_str = item['snippet']['publishedAt']
                published_at = datetime.strptime(
                    published_at_str, '%Y-%m-%dT%H:%M:%SZ'
                ).replace(tzinfo=timezone.utc)

                if published_at < cutoff:
                    stop = True
                    break

                video_id = item['snippet']['resourceId']['videoId']
                video_ids.append(video_id)

            if stop or not response.get('nextPageToken'):
                break
            next_page_token = response['nextPageToken']

        if not video_ids:
            return []
        return self.get_video_details(video_ids)

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """영상 ID 목록으로 제목·설명·날짜 등 상세 정보 반환"""
        response = self._service.videos().list(
            id=','.join(video_ids),
            part='id,snippet'
        ).execute()

        return [
            {
                'video_id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'published_at': item['snippet']['publishedAt'],
                'url': f"https://www.youtube.com/watch?v={item['id']}"
            }
            for item in response.get('items', [])
        ]
