"""
OpenAI / Gemini / Custom LLM implementation for extracting location info from Xiaohongshu notes.
Supports multi-place extraction (1 to 5 spots per note) with travel-aware destination disambiguation.
"""

import json
import re
from typing import List, Optional
from config import config
from src.models.place import NoteData, ExtractedLocation
from src.llm.base import BaseLLMExtractor


MULTI_EXTRACTION_SYSTEM_PROMPT = """你是一个高精度的全球旅游与美食地图专家。你的任务是从用户给出的「小红书」笔记标题、正文、标签和定位信息中，准确提取出笔记中【推荐或提到的具体打卡地点/店名/餐厅/景点/酒吧/项目】。

请输出包含 "places" 数组的 JSON 对象，每个地点元素符合以下结构：
{
  "places": [
    {
      "place_name": "具体店名或景点完整全称，如：Founding Fathers Pub / Trans-Canada Trail / 武康大楼",
      "city_or_district": "实际目的地城市、州/省或国家，如：Buffalo, NY, USA / Toronto, Canada / 上海市静安区",
      "category": "分类，例如：Cafe / Restaurant / Sightseeing / Park / Bakery / Bar / Hotel / Shopping / Other",
      "search_query": "适合在 Google Maps 搜索的最佳关键词组合（完整店名+目的地城市/州/国），如：Founding Fathers Pub Buffalo NY 或 Trans-Canada Trail Ontario",
      "summary": "用1-2句话简要总结笔记中对该地点的核心推荐理由或亮点特色",
      "confidence": 0.95
    }
  ]
}

⚠️ 极其关键的提取规则：
1. **完整名称原则**：必须提取完整精确的店铺或景点全称（如 "Founding Fathers Pub"），严禁截断词尾（如绝对不能提取为 "Founding" 或 "Pub"）。
2. **目的地 vs 出发地区分（跨国/自驾/旅行笔记）**：
   - 如果笔记描述的是自驾或跨城/跨国旅行（例如“从多伦多自驾去美国水牛城一日游”），提取的城市与国家必须是**目的地**（Buffalo, NY, USA），绝对不能把出发地（多伦多/Markham）或博主主页标签（如“#生活在多伦多”）误判为目的地！
3. **search_query 构造**：
   - 必须是 `"[完整店名/景点名] [目的地城市/州/国家]"`, 方便 Google Maps 精确检索。
   - 严禁包含“自驾”、“一日游”、“打卡”等无关修饰词。
4. **多地点提取**：如果笔记推荐了多个具体的店铺/景点，请依次提取核心打卡点（最多 5 个）。
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
正文内容/分享文本:
{note.desc[:2500]}
"""

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MULTI_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"} if "gpt" in self.model.lower() else None,
                temperature=0.1,
                max_tokens=1200,
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
                if not place_name or len(place_name) < 2:
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

        # Match location string after 📍 until colon/newline/punctuation (allow spaces inside English names)
        location_match = re.search(r"📍\s*([^\n\r：:，,！!?？;；]+)", note.desc + " " + note.title)
        if location_match:
            candidate = location_match.group(1).strip()
            # Clean trailing descriptive text after space if separated by punctuation
            candidate = re.sub(r"\s*[\(（\[【].*", "", candidate).strip()
            if candidate:
                place_name = candidate

        # Detect destination city vs blogger home city tags
        text_corpus = note.title + " " + note.desc
        destination_city = ""
        # Check explicit destination hints first
        for city in ["水牛城", "Buffalo", "多伦多", "Toronto", "温哥华", "Vancouver", "纽约", "New York", "上海", "北京", "东京", "Tokyo"]:
            if city in text_corpus:
                destination_city = city
                break

        if not destination_city and note.tags:
            destination_city = note.tags[0]

        search_query = f"{place_name} {destination_city}".strip()
        summary = note.desc[:120] + "..." if len(note.desc) > 120 else (note.desc or note.title)

        return ExtractedLocation(
            place_name=place_name,
            city_or_district=destination_city or None,
            category="Attraction",
            search_query=search_query,
            summary=summary or "Spot extracted from Xiaohongshu note.",
            confidence=0.6,
        )
