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

    def analyze_video(self, title: str, description: str) -> dict:
        """영상 제목과 설명으로 인사이트, 키워드, 요약, 주제, 중요도 추출"""
        content = f"제목: {title}\n\n설명:\n{description[:4000]}"
        prompt = f"""당신은 글로벌 AI 트렌드를 분석하는 전문 에디터입니다.
아래 유튜브 영상을 분석해 칼럼니스트가 글을 쓰는 데 쓸 수 있는 재료를 추출하세요.

아래 형식의 JSON만 출력하세요 (다른 텍스트 없이):
{{
  "summary": "이 영상이 왜 지금 중요한지 맥락을 포함한 한 문장",
  "insights": [
    "구체적 사실이나 주장 — 수치·이름·기술명 포함해서",
    "기존 통념과 다른 점 또는 업계에 미치는 영향",
    "글에 인용하거나 논거로 쓸 수 있는 포인트"
  ],
  "keywords": ["핵심키워드1", "핵심키워드2", "핵심키워드3", "핵심키워드4", "핵심키워드5"],
  "topic": "LLM/언어모델 | 멀티모달 | AI 에이전트 | 로보틱스 | AI 정책/윤리 | AI 비즈니스 | 연구/논문 중 하나",
  "importance": "🔥 높음 | ⭐ 보통 | 📌 낮음 중 하나",
  "writing_angle": "이 영상을 바탕으로 쓸 수 있는 칼럼·기사 아이디어 한 문장"
}}

영상 정보:
{content}"""

        response = self._model.generate_content(prompt)
        return self._parse_json_response(response.text)

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

    def generate_weekly_report(self, insights_data: list[dict]) -> dict:
        """지난 주 인사이트 목록으로 에디터 수준의 주간 리포트 생성"""
        video_list = '\n'.join(
            f"- [{item.get('topic', '기타')}] {item['title']} ({item.get('importance', '')})\n  요약: {item['summary']}\n  인사이트: {'; '.join(item.get('insights', []))}"
            for item in insights_data
        )
        prompt = f"""당신은 글로벌 AI 트렌드를 분석하는 시니어 에디터입니다.
이번 주 모니터링된 AI 유튜브 채널들의 분석 결과를 바탕으로,
AI 흐름을 파악하고 칼럼·기사를 쓰려는 전문가를 위한 주간 리포트를 작성하세요.

아래 형식의 JSON만 출력하세요:
{{
  "headline": "이번 주 AI 세계를 한 문장으로 (신문 헤드라인 스타일)",
  "main_narrative": "이번 주 가장 중요한 흐름과 맥락을 3-4문단으로. 단순 나열이 아니라 '왜 지금 이게 중요한가', '어떤 변화가 일어나고 있는가'를 중심으로 서술.",
  "key_themes": [
    {{"theme": "주제명", "description": "이 주제가 이번 주 어떻게 전개됐는지 2-3문장"}},
    {{"theme": "주제명", "description": "..."}},
    {{"theme": "주제명", "description": "..."}}
  ],
  "writing_angles": [
    {{"title": "칼럼/기사 제목 아이디어", "angle": "어떤 논점으로 쓸 수 있는지 구체적으로"}},
    {{"title": "...", "angle": "..."}},
    {{"title": "...", "angle": "..."}}
  ],
  "watch_next": "다음 주에 주목해야 할 것 — 이번 주 흐름이 어디로 향하는지"
}}

이번 주 분석된 영상들:
{video_list}"""

        response = self._model.generate_content(prompt)
        return self._parse_json_response(response.text)

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
