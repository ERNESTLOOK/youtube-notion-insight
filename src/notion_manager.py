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
        insights_text = '\n'.join(f"• {i}" for i in analysis.get('insights', []))
        writing_angle = analysis.get('writing_angle', '')
        topic = analysis.get('topic', '기타')
        importance = analysis.get('importance', '⭐ 보통')

        properties = {
            '영상 제목': {'title': [{'text': {'content': video['title']}}]},
            '채널명': {'relation': [{'id': channel['notion_page_id']}]},
            '분야': {'multi_select': [{'name': t} for t in channel['tags']]},
            '업로드 날짜': {'date': {'start': video['published_at'][:10]}},
            '트렌드 키워드': {
                'multi_select': [{'name': k} for k in analysis.get('keywords', [])]
            },
            '한줄 요약': {'rich_text': [{'text': {'content': analysis.get('summary', '')}}]},
            '원본 링크': {'url': video['url']},
            '영상 ID': {'rich_text': [{'text': {'content': video['video_id']}}]},
            '주제': {'multi_select': [{'name': topic}]},
            '중요도': {'select': {'name': importance}},
        }

        children = [
            {
                'object': 'block', 'type': 'heading_3',
                'heading_3': {'rich_text': [{'text': {'content': '핵심 인사이트'}}]}
            },
            {
                'object': 'block', 'type': 'paragraph',
                'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': insights_text}}]}
            },
        ]
        if writing_angle:
            children += [
                {
                    'object': 'block', 'type': 'heading_3',
                    'heading_3': {'rich_text': [{'text': {'content': '✍️ 글쓰기 앵글'}}]}
                },
                {
                    'object': 'block', 'type': 'callout',
                    'callout': {
                        'icon': {'type': 'emoji', 'emoji': '💡'},
                        'rich_text': [{'type': 'text', 'text': {'content': writing_angle}}]
                    }
                },
            ]

        self._client.pages.create(
            parent={'database_id': self._insight_db_id},
            properties=properties,
            children=children
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
            filter={'property': '업로드 날짜', 'date': {'on_or_after': cutoff}}
        )
        results = []
        for page in response['results']:
            props = page['properties']
            title_items = props['영상 제목']['title']
            summary_items = props['한줄 요약']['rich_text']
            keywords = [k['name'] for k in props['트렌드 키워드']['multi_select']]
            domains = [d['name'] for d in props['분야']['multi_select']]
            topics = [t['name'] for t in props.get('주제', {}).get('multi_select', [])]
            importance = props.get('중요도', {}).get('select') or {}
            # 본문에서 인사이트 텍스트 가져오기 (별도 API 호출 없이 요약으로 대체)
            page_id = page['id'].replace('-', '')
            notion_url = f"https://www.notion.so/{page_id}"
            results.append({
                'title': title_items[0]['text']['content'] if title_items else '',
                'summary': summary_items[0]['text']['content'] if summary_items else '',
                'keywords': keywords,
                'domain': domains[0] if domains else '기타',
                'topic': topics[0] if topics else '기타',
                'importance': importance.get('name', '⭐ 보통'),
                'url': props['원본 링크']['url'] or '',
                'notion_url': notion_url,
                'insights': [],
            })
        return results

    def create_weekly_report_page(self, week_label: str, report: dict, insights: list[dict]) -> None:
        """주간 AI 리포트 노션 페이지 생성 — 에디터 수준 내러티브"""

        def para(text: str) -> dict:
            return {'object': 'block', 'type': 'paragraph',
                    'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': text}}]}}

        def h2(text: str) -> dict:
            return {'object': 'block', 'type': 'heading_2',
                    'heading_2': {'rich_text': [{'text': {'content': text}}]}}

        def h3(text: str) -> dict:
            return {'object': 'block', 'type': 'heading_3',
                    'heading_3': {'rich_text': [{'text': {'content': text}}]}}

        def divider() -> dict:
            return {'object': 'block', 'type': 'divider', 'divider': {}}

        def callout(text: str, emoji: str = '💡') -> dict:
            return {'object': 'block', 'type': 'callout',
                    'callout': {'icon': {'type': 'emoji', 'emoji': emoji},
                                'rich_text': [{'type': 'text', 'text': {'content': text}}]}}

        def bullet(text: str, url: str = '') -> dict:
            rich = [{'type': 'text', 'text': {'content': text, 'link': {'url': url} if url else None}}]
            return {'object': 'block', 'type': 'bulleted_list_item',
                    'bulleted_list_item': {'rich_text': rich}}

        # 헤드라인
        headline = report.get('headline', f'{week_label} AI 동향')

        # 핵심 주제 블록
        theme_blocks = []
        for t in report.get('key_themes', []):
            theme_blocks += [h3(f"▸ {t['theme']}"), para(t['description'])]

        # 글쓰기 앵글 블록
        angle_blocks = []
        for i, a in enumerate(report.get('writing_angles', []), 1):
            angle_blocks += [
                callout(f"[아이디어 {i}] {a['title']}\n{a['angle']}", '✍️')
            ]

        # 이번 주 영상 목록 — 노션 페이지 링크 + 유튜브 링크 병기
        important = [v for v in insights if '높음' in v.get('importance', '')]
        show_list = (important or insights)[:5]
        video_bullets = []
        for v in show_list:
            topic = v.get('topic', '기타')
            notion_url = v.get('notion_url', '')
            yt_url = v.get('url', '')
            video_bullets.append({
                'object': 'block', 'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [
                        {'type': 'text', 'text': {'content': f'[{topic}] '}},
                        {'type': 'text', 'text': {
                            'content': v['title'],
                            'link': {'url': notion_url} if notion_url else None
                        }},
                        {'type': 'text', 'text': {
                            'content': ' ↗',
                            'link': {'url': yt_url} if yt_url else None
                        }},
                        {'type': 'text', 'text': {'content': f'\n→ {v.get("summary", "")}'}},
                    ]
                }
            })

        children = [
            callout(headline, '🌍'),
            divider(),
            h2('🌊 이번 주 핵심 흐름'),
            para(report.get('main_narrative', '')),
            divider(),
            h2('🔬 주제별 동향'),
            *theme_blocks,
            divider(),
            h2('✍️ 글쓰기 앵글 제안'),
            para('이번 주 AI 흐름을 바탕으로 바로 쓸 수 있는 칼럼·기사 아이디어:'),
            *angle_blocks,
            divider(),
            h2('📌 이번 주 주목할 영상'),
            *video_bullets,
            divider(),
            h2('🔭 다음 주 주목할 것'),
            callout(report.get('watch_next', ''), '👀'),
        ]

        self._client.pages.create(
            parent={'page_id': self._trend_parent_id},
            icon={'type': 'emoji', 'emoji': '🌍'},
            properties={'title': [{'text': {'content': f'🌍 {week_label} 글로벌 AI 동향 리포트'}}]},
            children=children
        )

    def update_dashboard(self, dashboard_page_id: str, today_insights: list[dict]) -> None:
        """메인 대시보드 페이지를 오늘 인사이트로 갱신"""

        def para(text: str) -> dict:
            return {'object': 'block', 'type': 'paragraph',
                    'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': text}}]}}

        def h2(text: str) -> dict:
            return {'object': 'block', 'type': 'heading_2',
                    'heading_2': {'rich_text': [{'text': {'content': text}}]}}

        def divider() -> dict:
            return {'object': 'block', 'type': 'divider', 'divider': {}}

        # 기존 블록 전체 삭제 후 새로 씀
        existing = self._client.blocks.children.list(block_id=dashboard_page_id)
        for block in existing.get('results', []):
            self._client.blocks.delete(block_id=block['id'])

        today_str = datetime.now(timezone.utc).strftime('%Y년 %m월 %d일')
        important = [v for v in today_insights if '높음' in v.get('importance', '')]
        others = [v for v in today_insights if '높음' not in v.get('importance', '')]

        blocks = [
            {'object': 'block', 'type': 'callout',
             'callout': {'icon': {'type': 'emoji', 'emoji': '📡'},
                         'rich_text': [{'type': 'text', 'text': {'content': f'마지막 업데이트: {today_str} | 오늘 새 영상 {len(today_insights)}개 분석'}}]}},
            divider(),
        ]

        if important:
            blocks += [h2('🔥 오늘 주목할 영상')]
            for v in important:
                blocks += [
                    {'object': 'block', 'type': 'callout',
                     'callout': {
                         'icon': {'type': 'emoji', 'emoji': '🎯'},
                         'rich_text': [
                             {'type': 'text', 'text': {'content': v['title'], 'link': {'url': v.get('url', '')}}},
                             {'type': 'text', 'text': {'content': f"\n{v.get('summary', '')}"}},
                         ]
                     }},
                ]
            blocks.append(divider())

        if others:
            blocks += [h2('📺 오늘 분석된 영상')]
            for v in others:
                topic = v.get('topic', '기타')
                summary = v.get('summary', '')
                url = v.get('url', '')
                blocks.append({
                    'object': 'block', 'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [
                            {'type': 'text', 'text': {'content': f'[{topic}] ', }},
                            {'type': 'text', 'text': {'content': v['title'], 'link': {'url': url} if url else None}},
                            {'type': 'text', 'text': {'content': f'\n→ {summary}'}},
                        ]
                    }
                })
            blocks.append(divider())

        if not today_insights:
            blocks.append(para('오늘은 새로 분석된 영상이 없습니다.'))

        self._client.blocks.children.append(block_id=dashboard_page_id, children=blocks)

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
