"""
OpenAI / Gemini / Custom LLM implementation for extracting location info from Xiaohongshu notes.
"""

import json
import re
from typing import Optional
from config import config
from src.models.place import NoteData, ExtractedLocation
from src.llm.base import BaseLLMExtractor


EXTRACTION_SYSTEM_PROMPT = """你是一个专业的旅游与美食地图助手。你的任务是从用户给出的「小红书」笔记标题、正文、标签和定位信息中，准确提取出笔记中推荐或提到的【具体地点/店名/景点/机构】。

请输出符合以下 JSON 格式的数据：
{
  "place_name": "具体店名或景点名称，如：BRUT CAFE / 武康大楼 / 蓝瓶咖啡(愚园路店)",
  "city_or_district": "提及的城市、区县或街区，如：上海市静安区愚园路",
  "category": "分类，例如：Cafe / Restaurant / Sightseeing / Bakery / Bar / Hotel / Shopping / Other",
  "search_query": "适合在谷歌地图(Google Maps)搜索的最佳关键词组合，如：BRUT CAFE Yuyuan Road Shanghai 或 武康大楼 Shanghai",
  "summary": "用1-2句话简要总结笔记中对该地点的核心推荐理由或亮点特色",
  "confidence": 0.95
}

注意规则：
1. place_name 必须尽量精简准确，不要包含修饰词（如“超级好吃的粉色咖啡馆” -> “XXX Cafe”）。
2. search_query 要包含英文或中文的标准名称 + 城市/街区，以便在 Google Maps 准确搜索到。
3. 如果笔记中提及多个地点，提取最核心推荐的主角地点。
4. 只返回合法的 JSON 对象，不要包含 markdown 代码块之外的多余文字。
"""


class OpenAIExtractor(BaseLLMExtractor):
    """LLM extractor using OpenAI SDK (compatible with OpenAI, Gemini, DeepSeek, etc.)"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = base_url or config.LLM_BASE_URL
        self.model = model or config.LLM_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                return None
            try:
                from openai import AsyncOpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except Exception:
                return None
        return self._client

    async def extract_location(self, note: NoteData) -> ExtractedLocation:
        """
        Extract location details using OpenAI API.
        Falls back to rule-based fallback extractor if API is unavailable or fails.
        """
        client = self._get_client()
        if not client:
            return self._heuristic_fallback_extraction(note)

        user_content = f"""【小红书笔记分析】
标题: {note.title}
定位/POI: {note.poi_name or '无'}
标签: {', '.join(note.tags) if note.tags else '无'}
正文内容:
{note.desc[:1500]}
"""

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"} if "gpt" in self.model.lower() else None,
                temperature=0.2,
                max_tokens=500,
            )

            raw_json = response.choices[0].message.content.strip()
            # Clean possible markdown block markers
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
                raw_json = re.sub(r"\n?```$", "", raw_json)

            data = json.loads(raw_json)
            return ExtractedLocation(
                place_name=data.get("place_name", note.title or "Unknown Spot"),
                city_or_district=data.get("city_or_district"),
                category=data.get("category", "Attraction"),
                search_query=data.get("search_query", f"{data.get('place_name')} {data.get('city_or_district', '')}"),
                summary=data.get("summary", "Xiaohongshu recommended spot"),
                confidence=float(data.get("confidence", 0.9)),
            )
        except Exception as e:
            # Fallback on API call error
            return self._heuristic_fallback_extraction(note)

    def _heuristic_fallback_extraction(self, note: NoteData) -> ExtractedLocation:
        """Rule-based heuristic fallback if LLM API key is not configured."""
        place_name = note.poi_name or note.title or "Recommended Spot"
        # Extract location keyword hints from tags or title
        city_hint = ""
        for tag in note.tags:
            if any(c in tag for c in ["上海", "北京", "广州", "深圳", "东京", "京都", "静安", "黄浦", "朝阳", "徐汇"]):
                city_hint = tag
                break

        search_query = f"{place_name} {city_hint}".strip()
        summary = note.desc[:100] + "..." if len(note.desc) > 100 else (note.desc or note.title)

        return ExtractedLocation(
            place_name=place_name,
            city_or_district=city_hint or None,
            category="Attraction",
            search_query=search_query,
            summary=summary or "Spot extracted from Xiaohongshu note.",
            confidence=0.6,
        )
