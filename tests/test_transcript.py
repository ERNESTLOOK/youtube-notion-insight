from unittest.mock import patch
from src.transcript import get_transcript


def test_get_transcript_success():
    """자막이 있으면 텍스트로 합쳐서 반환"""
    fake_transcript = [
        {'text': '안녕하세요', 'start': 0.0, 'duration': 1.0},
        {'text': '오늘은', 'start': 1.0, 'duration': 1.0},
    ]
    with patch('src.transcript.YouTubeTranscriptApi.get_transcript', return_value=fake_transcript):
        result = get_transcript('vid001')
    assert result == '안녕하세요 오늘은'


def test_get_transcript_no_transcript():
    """자막 없으면 None 반환"""
    from youtube_transcript_api import NoTranscriptFound
    with patch('src.transcript.YouTubeTranscriptApi.get_transcript',
               side_effect=NoTranscriptFound('vid001', ['ko', 'en'], {})):
        result = get_transcript('vid001')
    assert result is None


def test_get_transcript_disabled():
    """자막 비활성화된 영상은 None 반환"""
    from youtube_transcript_api import TranscriptsDisabled
    with patch('src.transcript.YouTubeTranscriptApi.get_transcript',
               side_effect=TranscriptsDisabled('vid001')):
        result = get_transcript('vid001')
    assert result is None
