import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled


def _make_api() -> YouTubeTranscriptApi:
    """쿠키 파일이 있으면 인증된 API 인스턴스 반환, 없으면 기본 인스턴스."""
    cookie_path = os.environ.get('YOUTUBE_COOKIE_PATH', 'cookies.txt')
    if os.path.exists(cookie_path):
        return YouTubeTranscriptApi(cookie_path=cookie_path)
    return YouTubeTranscriptApi()


def get_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
    """자막 추출. 자막 없거나 비활성화면 None 반환."""
    if languages is None:
        languages = ['ko', 'en']
    try:
        api = _make_api()
        result = api.fetch(video_id, languages=languages)
        return ' '.join(s.text for s in result)
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception:
        return None
