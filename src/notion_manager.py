from datetime import datetime, timedelta, timezone
from notion_client import Client


class NotionManager:
    def __init__(
        self,
        api_key: str,
        channel_db_id: str,
        insight_db_id: str,
        trend_parent_id: str,
    ):
        self._client = Client(auth=api_key)
        self._channel_db_id = channel_db_id
        self._insight_db_id = insight_db_id
        self._trend_parent_id = trend_parent_id

    def get_active_channels(self) -> list[dict]:
        """활성화 체크박스가 True인 채널 목록 반환"""
        response = self._client.databases.query(
            database_id=self._channel_db_id,
            filter={'property': '활성화', 'checkbox': {'equals': True}}
        )
        channels = []
        for page in response['results']:
            props = page['properties']
            channels.append({
                'notion_page_id': page['id'],
                'name': props['채널명']['title'][0]['text']['content'],
                'channel_id': props['채널 ID']['rich_text'][0]['text']['content'],
                'tags': [t['name'] for t in props['분야/태그']['multi_select']],
            })
        return channels

    def get_existing_video_ids(self) -> set[str]:
        """영상 인사이트 DB에 이미 저장된 영상 ID 집합 반환"""
        response = self._client.databases.query(database_id=self._insight_db_id)
        return {
            page['properties']['영상 ID']['rich_text'][0]['text']['content']
            for page in response['results']
            if page['properties']['영상 ID']['rich_text']
        }

    def save_insight(self, video: dict, channel: dict, analysis: dict) -> None:
        """영상 인사이트를 노션 DB에 저장"""
        insights_text = '\n'.join(f"• {i}" for i in analysis['insights'])
        self._client.pages.create(
            parent={'database_id': self._insight_db_id},
            properties={
                '영상 제목': {'title': [{'text': {'content': video['title']}}]},
                '채널명': {'relation': [{'id': channel['notion_page_id']}]},
                '분야': {'multi_select': [{'name': t} for t in channel['tags']]},
                '업로드 날짜': {'date': {'start': video['published_at'][:10]}},
                '트렌드 키워드': {
                    'multi_select': [{'name': k} for k in analysis['keywords']]
                },
                '한줄 요약': {'rich_text': [{'text': {'content': analysis['summary']}}]},
                '원본 링크': {'url': video['url']},
                '영상 ID': {'rich_text': [{'text': {'content': video['video_id']}}]},
            },
            children=[
                {
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{'type': 'text', 'text': {'content': insights_text}}]
                    }
                }
            ]
        )

    def update_channel_last_checked(self, notion_page_id: str) -> None:
        """채널 마지막 체크 날짜를 오늘로 업데이트"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self._client.pages.update(
            page_id=notion_page_id,
            properties={'마지막 체크': {'date': {'start': today}}}
        )

    def get_recent_insights(self, days: int = 7) -> list[dict]:
        """최근 N일간 저장된 인사이트 목록 반환"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        response = self._client.databases.query(
            database_id=self._insight_db_id,
            filter={
                'property': '업로드 날짜',
                'date': {'on_or_after': cutoff}
            }
        )
        results = []
        for page in response['results']:
            props = page['properties']
            title_items = props['영상 제목']['title']
            summary_items = props['한줄 요약']['rich_text']
            keywords = [k['name'] for k in props['트렌드 키워드']['multi_select']]
            domains = [d['name'] for d in props['분야']['multi_select']]
            results.append({
                'title': title_items[0]['text']['content'] if title_items else '',
                'summary': summary_items[0]['text']['content'] if summary_items else '',
                'keywords': keywords,
                'domain': domains[0] if domains else '기타',
                'url': props['원본 링크']['url'] or '',
            })
        return results

    def create_weekly_trend_page(
        self,
        week_label: str,
        trend_text: str,
        top_keywords: list[str],
        top_videos: list[dict],
    ) -> None:
        """주간 트렌드 노션 페이지 생성"""
        keyword_text = ', '.join(top_keywords[:10])
        video_bullets = [
            {
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {'content': v['title'], 'link': {'url': v['url']}}
                        }
                    ]
                }
            }
            for v in top_videos[:3]
        ]
        self._client.pages.create(
            parent={'page_id': self._trend_parent_id},
            properties={
                'title': [{'text': {'content': f'📊 주간 트렌드 — {week_label}'}}]
            },
            children=[
                {
                    'object': 'block', 'type': 'heading_2',
                    'heading_2': {'rich_text': [{'text': {'content': '이번 주 트렌드 키워드'}}]}
                },
                {
                    'object': 'block', 'type': 'paragraph',
                    'paragraph': {'rich_text': [{'text': {'content': keyword_text}}]}
                },
                {
                    'object': 'block', 'type': 'heading_2',
                    'heading_2': {'rich_text': [{'text': {'content': '주목할 영상 3선'}}]}
                },
                *video_bullets,
                {
                    'object': 'block', 'type': 'heading_2',
                    'heading_2': {'rich_text': [{'text': {'content': 'Gemini 트렌드 해석'}}]}
                },
                {
                    'object': 'block', 'type': 'paragraph',
                    'paragraph': {'rich_text': [{'text': {'content': trend_text}}]}
                },
            ]
        )

    def add_channel(self, channel: dict) -> None:
        """채널 목록 DB에 새 채널 추가"""
        self._client.pages.create(
            parent={'database_id': self._channel_db_id},
            properties={
                '채널명': {'title': [{'text': {'content': channel['name']}}]},
                '채널 ID': {'rich_text': [{'text': {'content': channel['channel_id']}}]},
                '분야/태그': {'multi_select': [{'name': t} for t in channel['tags']]},
                '활성화': {'checkbox': True},
            }
        )
