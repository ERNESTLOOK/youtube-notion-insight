import os
import requests
from http.cookiejar import MozillaCookieJar
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled


def _make_api() -> YouTubeTranscriptApi:
    """쿠키 파일이 있으면 인증된 세션으로 API 인스턴스 반환."""
    cookie_path = os.environ.get('YOUTUBE_COOKIE_PATH', 'cookies.txt')
    if os.path.exists(cookie_path):
        session = requests.Session()
        jar = MozillaCookieJar(cookie_path)
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies = jar
        return YouTubeTranscriptApi(http_client=session)
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
    except Exception as e:
        # IpBlocked, VideoUnavailable 등 모두 스킵
        return None
