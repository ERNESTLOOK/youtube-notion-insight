import json
import google.generativeai as genai


class GeminiAnalyzer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel('gemini-2.5-flash')

    def _parse_json_response(self, text: str) -> dict | list:
        """마크다운 코드블록 제거 후 JSON 파싱"""
        text = text.strip()
        if text.startswith('```'):
            parts = text.split('```')
            text = parts[1]
            if text.startswith('json'):
                text = text[4:]
        return json.loads(text.strip())

    def analyze_transcript(self, transcript: str, title: str) -> dict:
        """트랜스크립트에서 인사이트, 키워드, 요약 추출"""
        prompt = f"""다음은 유튜브 영상 "{title}"의 자막입니다.

아래 형식의 JSON만 출력하세요 (다른 텍스트 없이):
{{
  "insights": ["인사이트1", "인사이트2", "인사이트3"],
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "summary": "한 문장 요약"
}}

규칙:
- insights: 글 재료로 쓸 수 있는 구체적인 핵심 인사이트 3-5개
- keywords: 이 영상의 핵심 트렌드 키워드 정확히 5개
- summary: 글 재료로 바로 활용 가능한 한 문장

자막 (최대 8000자):
{transcript[:8000]}"""

        response = self._model.generate_content(prompt)
        return self._parse_json_response(response.text)

    def analyze_weekly_trend(self, insights_data: list[dict]) -> str:
        """지난 주 인사이트 목록에서 트렌드 해석 텍스트 생성"""
        summaries = '\n'.join(
            f"- [{item['domain']}] {item['title']}: {item['summary']}"
            for item in insights_data
        )
        prompt = f"""지난 한 주간 다음 유튜브 영상들이 분석되었습니다:

{summaries}

이 영상들을 바탕으로 이번 주 전문 분야의 트렌드를 2-3문단으로 해석해주세요.
글 작성자의 관점에서, 어떤 흐름이 보이는지 구체적으로 작성하세요."""

        response = self._model.generate_content(prompt)
        return response.text.strip()

    def suggest_channels(self, domain: str) -> list[dict]:
        """분야 키워드로 인기 유튜브 채널 추천"""
        prompt = f""""{domain}" 분야의 인기 유튜브 채널을 5개 추천해주세요.

아래 형식의 JSON 배열만 출력하세요 (다른 텍스트 없이):
[
  {{"name": "채널명", "channel_id": "@핸들또는UCxxxxxx", "tags": ["태그1", "태그2"]}},
  ...
]

실제 존재하는 채널만 추천하세요."""

        response = self._model.generate_content(prompt)
        return self._parse_json_response(response.text)
