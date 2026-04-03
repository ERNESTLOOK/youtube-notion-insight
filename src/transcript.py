from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)


def get_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
    """자막 추출. 자막 없거나 비활성화면 None 반환."""
    if languages is None:
        languages = ['ko', 'en']
    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return ' '.join(entry['text'] for entry in entries)
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
