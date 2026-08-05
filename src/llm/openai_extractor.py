"""
OpenAI / Gemini / Custom LLM implementation for extracting location info from Xiaohongshu notes.
Supports multi-place extraction (1 to 5 spots per note) with travel-aware destination disambiguation.
Includes robust rule-based multi-location parsing and smart summary generator as fallback.
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
      "summary": "请用你自己提炼的1-2句精炼中文推荐理由（说明该地点的亮点特色、招牌推荐或氛围），绝对不要原封不动复制整段原文！",
      "confidence": 0.95
    }
  ]
}

⚠️ 极其关键的提取规则：
1. **精炼 Summary 原则**：summary 必须是 AI 重新总结归纳的 1-2 句看点（如“水牛城特色复古 Pub，老美氛围感极佳，人均20刀”），绝对不能把整段长篇大论的原文本复制过来！
2. **完整名称原则**：必须提取完整精确的店铺或景点全称（如 "Founding Fathers Pub"），严禁截断词尾（如绝对不能提取为 "Founding" 或 "Pub"）。
3. **目的地 vs 出发地区分（跨国/自驾/旅行笔记）**：
   - 如果笔记描述的是自驾或跨城/跨国旅行（例如“从多伦多自驾去美国水牛城一日游”），提取的城市与国家必须是**目的地**（Buffalo, NY, USA），绝对不能把出发地（多伦多/Markham）或博主主页标签（如“#生活在多伦多”）误判为目的地！
4. **search_query 构造**：
   - 必须是 `"[完整店名/景点名] [目的地城市/州/国家]"`, 方便 Google Maps 精确检索。
   - 严禁包含“自驾”、“一日游”、“打卡”等无关修饰词。
5. **多地点提取**：如果笔记推荐了多个具体的店铺/景点，请依次提取所有打卡点（最多 5 个）。
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
            if not self.api_key or "your_" in self.api_key.lower():
                print("⚠️ LLM_API_KEY 未设置或为默认占位符！将使用本地规则提取备用流程。")
                return None
            try:
                from openai import AsyncOpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except Exception as e:
                print(f"⚠️ 初始化 OpenAI 客户端失败: {e}")
                return None
        return self._client

    async def extract_location(self, note: NoteData) -> ExtractedLocation:
        """Extract primary single location."""
        locations = await self.extract_locations(note)
        return locations[0]

    async def extract_locations(self, note: NoteData) -> List[ExtractedLocation]:
        """Extract ALL locations mentioned in note (1 to 5 spots)."""
        client = self._get_client()
        if not client:
            return self._heuristic_fallback_extractions(note)

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
                temperature=0.2,
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
                        summary=item.get("summary", f"小红书推荐打卡地: {place_name}"),
                        confidence=float(item.get("confidence", 0.95)),
                    )
                )

            return results if results else self._heuristic_fallback_extractions(note)

        except Exception as e:
            print(f"⚠️ LLM API 调用失败 ({e})，自动切换至本地多地点规则提取备用流程。")
            return self._heuristic_fallback_extractions(note)

    def _heuristic_fallback_extraction(self, note: NoteData) -> ExtractedLocation:
        """Backward compatibility wrapper returning primary fallback location."""
        locations = self._heuristic_fallback_extractions(note)
        return locations[0]

    def _heuristic_fallback_extractions(self, note: NoteData) -> List[ExtractedLocation]:
        """Smart rule-based multi-location extraction fallback when LLM API key is not configured or errors out."""
        text_corpus = note.title + "\n" + note.desc

        # Detect destination city
        destination_city = ""
        for city in ["水牛城", "Buffalo", "多伦多", "Toronto", "温哥华", "Vancouver", "纽约", "New York", "上海", "北京", "东京", "Tokyo"]:
            if city in text_corpus:
                destination_city = city
                break

        # Filter keywords for invalid place names
        INVALID_STARTS = ("我们", "大家", "吃了", "玩了", "晚上", "小城", "因为", "原本", "记得", "非常", "虽然", "后来")

        # Match ALL locations with 📍 emoji or numbered markers 1️⃣ 2️⃣
        matches = re.findall(r"(?:📍|\d+️⃣)\s*([^\n\r：:，,！!?？;；\(\（]+)(?:[:：\s]*([^\n\r📍]+))?", text_corpus)

        results = []
        seen = set()

        for place_match, desc_snippet in matches:
            place_name = place_match.strip()
            # Clean unwanted brackets or words
            place_name = re.sub(r"[\(（\[【].*", "", place_name).strip()
            if not place_name or len(place_name) < 2 or len(place_name) > 30 or place_name in seen:
                continue
            if any(place_name.startswith(bad) for bad in INVALID_STARTS):
                continue

            seen.add(place_name)

            # Generate smart summary snippet (1 sentence summary)
            raw_sum = desc_snippet.strip() if desc_snippet else ""
            if raw_sum:
                # Take first sentence of snippet
                sum_sentence = re.split(r"[。！!？?\n]", raw_sum)[0].strip()
                summary = f"笔记推荐打卡点：{sum_sentence[:60]}" if sum_sentence else f"笔记推荐热门打卡地: {place_name}"
            else:
                summary = f"笔记推荐热门打卡地: {place_name}"

            search_query = f"{place_name} {destination_city}".strip()
            results.append(
                ExtractedLocation(
                    place_name=place_name,
                    city_or_district=destination_city or None,
                    category="Restaurant" if any(k in place_name.lower() for k in ["pub", "grill", "cafe", "餐", "馆", "店"]) else "Attraction",
                    search_query=search_query,
                    summary=summary,
                    confidence=0.7,
                )
            )

        # If no 📍 found, fallback to title or POI name
        if not results:
            place_name = note.poi_name or note.title or "Recommended Spot"
            search_query = f"{place_name} {destination_city}".strip()
            summary = f"小红书推荐打卡地: {place_name}"
            results.append(
                ExtractedLocation(
                    place_name=place_name,
                    city_or_district=destination_city or None,
                    category="Attraction",
                    search_query=search_query,
                    summary=summary,
                    confidence=0.6,
                )
            )

        return results
