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
        self._trend_parent_id = trend_parent_id        self._cloudmap_id = cloudmap_id        self._persons_db_id = persons_db_id        self._cloudmap_id = cloudmap_id

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

    def get_all_channel_ids(self) -> set[str]:
        """채널 목록 DB에 등록된 모든 채널 ID 집합 반환 (중복 방지용)"""
        results = []
        cursor = None
        while True:
            kwargs = {'database_id': self._channel_db_id}
            if cursor:
                kwargs['start_cursor'] = cursor
            response = self._client.databases.query(**kwargs)
            results.extend(response.get('results', []))
            if not response.get('has_more'):
                break
            cursor = response.get('next_cursor')

        ids = set()
        for page in results:
            items = page['properties']['채널 ID']['rich_text']
            if items:
                ids.add(items[0]['text']['content'])
        return ids

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

        thumbnail_url = f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg"
        self._client.pages.create(
            parent={'database_id': self._insight_db_id},
            cover={'type': 'external', 'external': {'url': thumbnail_url}},
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

    _USER_CONTEXT_EMOJI = '✏️'
    _USER_CONTEXT_PLACEHOLDER = (
        '💭 나의 핵심 맥락 — 여기에 직접 입력하세요.\n'
        '예) "이번 주 관심 주제: AI 에이전트 규제 / 강의 준비 중인 키워드: 멀티모달"\n'
        '(이 블록은 매일 자동 업데이트에도 삭제되지 않고 유지됩니다)'
    )

    def _read_user_context(self, dashboard_page_id: str) -> list[dict]:
        """대시보드 첫 번째 블록이 사용자 맥락 callout이면 rich_text를 반환, 아니면 []."""
        response = self._client.blocks.children.list(
            block_id=dashboard_page_id, page_size=1
        )
        blocks = response.get('results', [])
        if not blocks:
            return []
        first = blocks[0]
        if (first.get('type') == 'callout'
                and first.get('callout', {}).get('icon', {}).get('emoji') == self._USER_CONTEXT_EMOJI):
            return first['callout'].get('rich_text', [])
        return []

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

        # 사용자 맥락 블록 내용 먼저 보존
        saved_rich_text = self._read_user_context(dashboard_page_id)

        # 기존 블록 전체 삭제 후 새로 씀
        existing = self._client.blocks.children.list(block_id=dashboard_page_id)
        for block in existing.get('results', []):
            self._client.blocks.delete(block_id=block['id'])

        today_str = datetime.now(timezone.utc).strftime('%Y년 %m월 %d일')
        important = [v for v in today_insights if '높음' in v.get('importance', '')]
        others = [v for v in today_insights if '높음' not in v.get('importance', '')]

        # 사용자 맥락 블록 (보존된 내용 또는 초기 안내 문구)
        user_context_rich_text = saved_rich_text or [
            {'type': 'text', 'text': {'content': self._USER_CONTEXT_PLACEHOLDER}}
        ]
        user_context_block = {
            'object': 'block', 'type': 'callout',
            'callout': {
                'icon': {'type': 'emoji', 'emoji': self._USER_CONTEXT_EMOJI},
                'color': 'gray_background',
                'rich_text': user_context_rich_text,
            },
        }

        blocks = [
            user_context_block,
            divider(),
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


    def update_persons(self, persons_from_video: list[dict]) -> None:
                """영상 분석에서 추출된 인물들을 주요인물 목록 DB에 upsert"""
                if not self._persons_db_id or not persons_from_video:
                                return
                            # 기존 인물 이름 목록 조회
                            response = self._client.databases.query(database_id=self._persons_db_id)
                existing = {}
                for page in response['results']:
                                props = page['properties']
                                title_items = props.get('인물명', {}).get('title', [])
                                if title_items:
                                                    name = title_items[0]['text']['content']
                                                    existing[name] = page['id']

                            for person in persons_from_video:
                                            name = person.get('name', '').strip()
                                            role = person.get('role', '').strip()
                                            domain = person.get('domain', '').strip()
                                            if not name:
                                                                continue

                                            if name in existing:
                                                                # 출연횟수 +1
                                                                page_id = existing[name]
                                                                page = self._client.pages.retrieve(page_id=page_id)
                                                                count = page['properties'].get('출연횟수', {}).get('number', 0) or 0
                                                                self._client.pages.update(
                                                                    page_id=page_id,
                                                                    properties={'출연횟수': {'number': count + 1}}
                                                                )
else:
                # 새 인물 추가
                    props = {
                                            '인물명': {'title': [{'text': {'content': name}}]},
                                            '출연횟수': {'number': 1},
                    }
                if role:
                                        props['소속/직함'] = {'rich_text': [{'text': {'content': role}}]}
                                    if domain:
                                                            props['관련 분야'] = {'multi_select': [{'name': domain}]}
                                                        self._client.pages.create(
                                                                                parent={'database_id': self._persons_db_id},
                                                                                properties=props
                                                        )
                existing[name] = True

    def update_cloudmap(self, insights: list[dict]) -> None:
                """주제별 연결 클라우드맵 페이지를 최신 인사이트 데이터 기준으로 갱신"""
                if not self._cloudmap_id or not insights:
                                return

                from collections import Counter, defaultdict

        # 주제별 영상 수 집계
                topic_counts = Counter(v.get('topic', '기타') for v in insights)
        # 주제 간 연결 관계 (같은 키워드를 공유하는 주제 쌍)
        topic_keywords = defaultdict(set)
        for v in insights:
                        topic = v.get('topic', '기타')
                        for kw in v.get('keywords', []):
                                            topic_keywords[topic].add(kw)

                    # 연결 관계 (공유 키워드 2개 이상인 주제 쌍)
                    topics = list(topic_counts.keys())
        connections = []
        for i in range(len(topics)):
                        for j in range(i + 1, len(topics)):
                                            shared = topic_keywords[topics[i]] & topic_keywords[topics[j]]
                                            if len(shared) >= 2:
                                                                    connections.append((topics[i], topics[j], list(shared)[:3]))

                                    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        total = len(insights)
        n_topics = len(topic_counts)
        n_connections = len(connections)

        # 기존 블록 전체 삭제
        existing = self._client.blocks.children.list(block_id=self._cloudmap_id)
        for block in existing.get('results', []):
                        self._client.blocks.delete(block_id=block['id'])

        # 상단 메타 정보 블록
        meta_text = f'데이터 기준: 전체 {total}편 · {n_topics}개 주제 · {n_connections}개 연결 관계 · 마지막 업데이트: {today_str}'
        blocks = [
                        {
                                            'object': 'block', 'type': 'callout',
                                            'callout': {
                                                                    'icon': {'type': 'emoji', 'emoji': '🗺️'},
                                                                    'rich_text': [{'type': 'text', 'text': {'content': meta_text}}]
                                            }
                        },
                        {'object': 'block', 'type': 'heading_2',
                                      'heading_2': {'rich_text': [{'text': {'content': '🧠 주제별 영상 분포'}}]}},
        ]

        # 주제별 영상 수 목록
        for topic, count in topic_counts.most_common():
                        bar = '█' * min(count, 20)
            blocks.append({
                                'object': 'block', 'type': 'paragraph',
                                'paragraph': {'rich_text': [{'type': 'text', 'text': {
                                                        'content': f'{topic}: {bar} ({count}편)'
                                }}]}
            })

        blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
        blocks.append({
                        'object': 'block', 'type': 'heading_2',
                        'heading_2': {'rich_text': [{'text': {'content': '🔗 주제 간 연결 관계'}}]}
        })

        if connections:
                        for t1, t2, shared_kws in connections:
                                            blocks.append({
                                                                    'object': 'block', 'type': 'bulleted_list_item',
                                                                    'bulleted_list_item': {'rich_text': [{'type': 'text', 'text': {
                                                                                                'content': f'{t1} ↔ {t2}  |  공유 키워드: {", ".join(shared_kws)}'
                                                                    }}]}
                                            })
else:
            blocks.append({
                                'object': 'block', 'type': 'paragraph',
                                'paragraph': {'rich_text': [{'type': 'text', 'text': {
                                                        'content': '아직 연결 관계가 형성될 만큼 데이터가 충분하지 않습니다.'
                                }}]}
            })

        self._client.blocks.children.append(block_id=self._cloudmap_id, children=blocks)
