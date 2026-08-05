"""
Unit tests for LLM location extraction.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.place import NoteData
from src.llm.openai_extractor import OpenAIExtractor


def test_heuristic_fallback_extraction():
    extractor = OpenAIExtractor(api_key="")  # No API key triggers fallback
    note = NoteData(
        url="https://www.xiaohongshu.com/explore/note123",
        note_id="note123",
        title="愚园路 BRUT CAFE",
        desc="上海市静安区愚园路超棒的咖啡馆！推荐拿铁",
        tags=["上海美食", "静安区咖啡"],
        poi_name="BRUT CAFE"
    )

    location = extractor._heuristic_fallback_extraction(note)
    assert location.place_name == "BRUT CAFE"
    assert "上海" in location.city_or_district or "静安" in location.city_or_district
    assert location.category == "Attraction"
    assert "BRUT CAFE" in location.search_query


@pytest.mark.asyncio
async def test_openai_mock_extraction():
    extractor = OpenAIExtractor(api_key="mock_key", model="gpt-4o-mini")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = """
    {
        "place_name": "BRUT CAFE",
        "city_or_district": "上海市静安区愚园路",
        "category": "Cafe",
        "search_query": "BRUT CAFE Yuyuan Road Shanghai",
        "summary": "上海静安区愚园路特色复古咖啡馆，环境优美拿铁赞。",
        "confidence": 0.95
    }
    """
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    extractor._client = mock_client

    note = NoteData(
        url="https://www.xiaohongshu.com/explore/note123",
        note_id="note123",
        title="愚园路 BRUT CAFE",
        desc="上海静安区愚园路复古咖啡馆",
    )

    loc = await extractor.extract_location(note)
    assert loc.place_name == "BRUT CAFE"
    assert loc.category == "Cafe"
    assert loc.search_query == "BRUT CAFE Yuyuan Road Shanghai"
    assert loc.confidence == 0.95
