"""
OpenAI / Gemini / Custom LLM implementation for extracting location info from Xiaohongshu notes.
Supports multi-place extraction (1 to 5 spots per note).
"""

import json
import re
from typing import List, Optional
from config import config
from src.models.place import NoteData, ExtractedLocation
from src.llm.base import BaseLLMExtractor


MULTI_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的旅游与美食地图助手。你的任务是从用户给出的「小红书」笔记标题、正文、标签和定位信息中，准确提取出笔记中【推荐或提到的所有具体地点/店名/景点/机构】（如果只有1个则提取1个，如果有多个合集推荐，最多提取最核心的 5 个）。

请输出包含 "places" 数组的 JSON 对象，每个地点元素符合以下结构：
{
  "places": [
    {
      "place_name": "具体店名或景点名称，如：Elora Town / BRUT CAFE / Trans-Canada Trail",
      "city_or_district": "提及的城市、区县或国家，如：Canada Toronto / 上海市静安区",
      "category": "分类，例如：Cafe / Restaurant / Sightseeing / Park / Bakery / Bar / Hotel / Shopping / Other",
      "search_query": "适合在 Google Maps 搜索的最佳关键词组合（英文/中文+城市名），如：Trans-Canada Trail Ontario Canada 或 Elora Town Ontario",
      "summary": "用1-2句话简要总结笔记中对该地点的核心推荐理由或亮点特色",
      "confidence": 0.95
    }
  ]
}

注意规则：
1. place_name 必须尽量精简准确，不要包含无用修饰词。
2. search_query 要包含英文或中文的标准名称 + 城市/地区，以便在 Google Maps 准确定位。
3. 如果笔记是多地点合集（如“多伦多周边3个小镇”、“上海5家咖啡馆”），请依次提取各个具体的地点名称。
4. 只返回合法的 JSON 对象。
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
        """Extract primary single location."""
        locations = await self.extract_locations(note)
        return locations[0] if locations else self._heuristic_fallback_extraction(note)

    async def extract_locations(self, note: NoteData) -> List[ExtractedLocation]:
        """Extract ALL locations mentioned in note (1 to 5 spots)."""
        client = self._get_client()
        if not client:
            return [self._heuristic_fallback_extraction(note)]

        user_content = f"""【小红书笔记分析】
标题: {note.title}
定位/POI: {note.poi_name or '无'}
标签: {', '.join(note.tags) if note.tags else '无'}
正文/分享文本:
{note.desc[:2000]}
"""

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MULTI_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"} if "gpt" in self.model.lower() else None,
                temperature=0.2,
                max_tokens=1000,
            )

            raw_json = response.choices[0].message.content.strip()
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
                raw_json = re.sub(r"\n?```$", "", raw_json)

            data = json.loads(raw_json)
            places_list = data.get("places", [])
            if not places_list and isinstance(data, dict) and "place_name" in data:
                places_list = [data]

            results = []
            for item in places_list:
                place_name = item.get("place_name", "").strip()
                if not place_name:
                    continue
                results.append(
                    ExtractedLocation(
                        place_name=place_name,
                        city_or_district=item.get("city_or_district"),
                        category=item.get("category", "Attraction"),
                        search_query=item.get("search_query", f"{place_name} {item.get('city_or_district', '')}"),
                        summary=item.get("summary", "Xiaohongshu recommended spot"),
                        confidence=float(item.get("confidence", 0.9)),
                    )
                )

            return results if results else [self._heuristic_fallback_extraction(note)]

        except Exception as e:
            return [self._heuristic_fallback_extraction(note)]

    def _heuristic_fallback_extraction(self, note: NoteData) -> ExtractedLocation:
        """Rule-based heuristic fallback if LLM API key is not configured or fails."""
        place_name = note.poi_name or note.title or "Recommended Spot"

        # Try regex pattern matching for location names in text (e.g. 📍Trans-Canada Trail)
        location_match = re.search(r"📍\s*([^\s\n\r,，!！]+)", note.desc + " " + note.title)
        if location_match:
            place_name = location_match.group(1).strip()

        city_hint = ""
        for tag in note.tags + [note.title, note.desc]:
            if any(c in tag for c in ["多伦多", "上海", "北京", "广州", "深圳", "东京", "京都", "温哥华"]):
                city_hint = tag
                break

        search_query = f"{place_name} {city_hint}".strip()
        summary = note.desc[:120] + "..." if len(note.desc) > 120 else (note.desc or note.title)

        return ExtractedLocation(
            place_name=place_name,
            city_or_district=city_hint or None,
            category="Attraction",
            search_query=search_query,
            summary=summary or "Spot extracted from Xiaohongshu note.",
            confidence=0.6,
        )
