from unittest.mock import MagicMock, patch
from src.youtube_client import YouTubeClient


def make_client():
    with patch('src.youtube_client.build') as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeClient(api_key='fake_key')
        client._service = mock_build.return_value
        return client


def test_resolve_channel_id_uc_format():
    """UCxxxxx 형식은 그대로 반환"""
    client = make_client()
    result = client.resolve_channel_id('UCabc123')
    assert result == 'UCabc123'


def test_resolve_channel_id_handle_format():
    """@handle 형식을 채널 ID로 변환"""
    client = make_client()
    client._service.channels.return_value.list.return_value.execute.return_value = {
        'items': [{'id': 'UCabc123'}]
    }
    result = client.resolve_channel_id('@testchannel')
    assert result == 'UCabc123'
    client._service.channels.return_value.list.assert_called_once_with(
        forHandle='testchannel', part='id'
    )


def test_get_recent_videos_returns_list():
    """최근 영상 목록을 딕셔너리 리스트로 반환"""
    client = make_client()
    client._service.search.return_value.list.return_value.execute.return_value = {
        'items': [
            {
                'id': {'videoId': 'vid001'},
                'snippet': {
                    'title': '테스트 영상',
                    'publishedAt': '2026-04-03T00:00:00Z'
                }
            }
        ]
    }
    result = client.get_recent_videos('UCabc123', hours=24)
    assert len(result) == 1
    assert result[0]['video_id'] == 'vid001'
    assert result[0]['title'] == '테스트 영상'
    assert result[0]['url'] == 'https://www.youtube.com/watch?v=vid001'
    assert result[0]['published_at'] == '2026-04-03T00:00:00Z'


def test_get_recent_videos_empty():
    """영상 없으면 빈 리스트 반환"""
    client = make_client()
    client._service.search.return_value.list.return_value.execute.return_value = {'items': []}
    result = client.get_recent_videos('UCabc123')
    assert result == []
