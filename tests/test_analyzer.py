import json
from unittest.mock import MagicMock, patch
from src.analyzer import GeminiAnalyzer


def make_analyzer():
    with patch('src.analyzer.genai.configure'):
        with patch('src.analyzer.genai.GenerativeModel') as mock_model_cls:
            analyzer = GeminiAnalyzer(api_key='fake_key')
            analyzer._model = mock_model_cls.return_value
            return analyzer


def test_analyze_transcript_returns_structured_data():
    """분석 결과에 insights, keywords, summary 포함"""
    analyzer = make_analyzer()
    fake_response = {
        'insights': ['인사이트1', '인사이트2', '인사이트3'],
        'keywords': ['키워드1', '키워드2', '키워드3', '키워드4', '키워드5'],
        'summary': '한줄 요약'
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(fake_response)
    analyzer._model.generate_content.return_value = mock_response

    result = analyzer.analyze_transcript('자막 텍스트', '영상 제목')

    assert result['insights'] == ['인사이트1', '인사이트2', '인사이트3']
    assert len(result['keywords']) == 5
    assert result['summary'] == '한줄 요약'


def test_analyze_transcript_handles_markdown_json():
    """```json ... ``` 마크다운 래핑된 응답도 파싱"""
    analyzer = make_analyzer()
    fake_response = {
        'insights': ['A'],
        'keywords': ['B'],
        'summary': 'C'
    }
    mock_response = MagicMock()
    mock_response.text = f"```json\n{json.dumps(fake_response)}\n```"
    analyzer._model.generate_content.return_value = mock_response

    result = analyzer.analyze_transcript('자막', '제목')
    assert result['summary'] == 'C'


def test_suggest_channels_returns_list():
    """채널 추천 결과가 name, channel_id, tags를 가진 딕셔너리 리스트"""
    analyzer = make_analyzer()
    fake_channels = [
        {'name': '채널A', 'channel_id': '@channelA', 'tags': ['AI']},
        {'name': '채널B', 'channel_id': 'UCabc', 'tags': ['교육']},
    ]
    mock_response = MagicMock()
    mock_response.text = json.dumps(fake_channels)
    analyzer._model.generate_content.return_value = mock_response

    result = analyzer.suggest_channels('AI 교육')
    assert len(result) == 2
    assert result[0]['name'] == '채널A'


def test_analyze_weekly_trend_returns_string():
    """주간 트렌드 해석이 비어있지 않은 문자열"""
    analyzer = make_analyzer()
    mock_response = MagicMock()
    mock_response.text = '이번 주 AI 트렌드는...'
    analyzer._model.generate_content.return_value = mock_response

    insights_data = [
        {'title': '영상1', 'keywords': ['AI', '교육'], 'summary': '요약1', 'domain': 'AI'}
    ]
    result = analyzer.analyze_weekly_trend(insights_data)
    assert isinstance(result, str)
    assert len(result) > 0
