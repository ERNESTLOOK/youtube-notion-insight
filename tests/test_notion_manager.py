from unittest.mock import MagicMock, patch
from src.notion_manager import NotionManager


def make_manager():
    with patch('src.notion_manager.Client') as mock_client_cls:
        manager = NotionManager(
            api_key='fake',
            channel_db_id='channel-db-id',
            insight_db_id='insight-db-id',
            trend_parent_id='trend-parent-id'
        )
        manager._client = mock_client_cls.return_value
        return manager


def test_get_active_channels():
    """활성화된 채널 목록 반환"""
    manager = make_manager()
    manager._client.databases.query.return_value = {
        'results': [
            {
                'id': 'page-id-1',
                'properties': {
                    '채널명': {'title': [{'text': {'content': '테스트채널'}}]},
                    '채널 ID': {'rich_text': [{'text': {'content': 'UCabc123'}}]},
                    '분야/태그': {'multi_select': [{'name': 'AI'}]},
                }
            }
        ]
    }
    result = manager.get_active_channels()
    assert len(result) == 1
    assert result[0]['name'] == '테스트채널'
    assert result[0]['channel_id'] == 'UCabc123'
    assert result[0]['tags'] == ['AI']
    assert result[0]['notion_page_id'] == 'page-id-1'


def test_get_existing_video_ids():
    """이미 저장된 영상 ID 집합 반환"""
    manager = make_manager()
    manager._client.databases.query.return_value = {
        'results': [
            {'properties': {'영상 ID': {'rich_text': [{'text': {'content': 'vid001'}}]}}},
            {'properties': {'영상 ID': {'rich_text': [{'text': {'content': 'vid002'}}]}}},
        ]
    }
    result = manager.get_existing_video_ids()
    assert result == {'vid001', 'vid002'}


def test_save_insight_calls_pages_create():
    """인사이트 저장 시 notion pages.create 호출"""
    manager = make_manager()
    video = {
        'video_id': 'vid001',
        'title': '테스트 영상',
        'published_at': '2026-04-03T00:00:00Z',
        'url': 'https://youtube.com/watch?v=vid001'
    }
    channel = {
        'notion_page_id': 'channel-page-id',
        'name': '테스트채널',
        'tags': ['AI']
    }
    analysis = {
        'insights': ['인사이트1', '인사이트2'],
        'keywords': ['키워드1', '키워드2'],
        'summary': '한줄요약'
    }
    manager.save_insight(video, channel, analysis)
    manager._client.pages.create.assert_called_once()
    call_kwargs = manager._client.pages.create.call_args[1]
    assert call_kwargs['parent']['database_id'] == 'insight-db-id'


def test_update_channel_last_checked():
    """채널 마지막 체크 날짜 업데이트"""
    manager = make_manager()
    manager.update_channel_last_checked('page-id-1')
    manager._client.pages.update.assert_called_once()
    call_kwargs = manager._client.pages.update.call_args[1]
    assert call_kwargs['page_id'] == 'page-id-1'


def test_add_channel():
    """채널 목록 DB에 새 채널 추가"""
    manager = make_manager()
    channel = {'name': '새채널', 'channel_id': '@newchannel', 'tags': ['교육']}
    manager.add_channel(channel)
    manager._client.pages.create.assert_called_once()
    call_kwargs = manager._client.pages.create.call_args[1]
    assert call_kwargs['parent']['database_id'] == 'channel-db-id'
