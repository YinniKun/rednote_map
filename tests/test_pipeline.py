"""
Integration unit test for ProcessPipeline.
"""

import pytest
from unittest.mock import AsyncMock
from src.models.place import NoteData, ExtractedLocation, GooglePlaceDetails
from src.services.pipeline import ProcessPipeline


@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    mock_parser = AsyncMock()
    mock_parser.parse.return_value = NoteData(
        url="https://www.xiaohongshu.com/explore/note789",
        note_id="note789",
        title="武康大楼打卡",
        desc="上海经典标志性历史建筑武康大楼",
        tags=["上海景点"],
        image_urls=["https://img.xhs.com/wukang.jpg"]
    )

    mock_extractor = AsyncMock()
    mock_extractor.extract_location.return_value = ExtractedLocation(
        place_name="武康大楼",
        city_or_district="上海市徐汇区淮海中路1850号",
        category="Sightseeing",
        search_query="武康大楼 Shanghai",
        summary="上海著名历史公寓建筑，超好拍。",
        confidence=0.98
    )

    mock_geocoder = AsyncMock()
    mock_geocoder.search_place.return_value = GooglePlaceDetails(
        place_id="wukang_123",
        name="武康大楼",
        formatted_address="1850 Huaihai Middle Rd, Xuhui District, Shanghai",
        latitude=31.2014,
        longitude=121.4426,
        google_maps_url="https://www.google.com/maps/place/?q=place_id:wukang_123"
    )

    mock_pinner = AsyncMock()
    mock_pinner.pin.return_value = (True, "📍 Pinned to Google My Maps!")

    pipeline = ProcessPipeline(
        parser=mock_parser,
        extractor=mock_extractor,
        geocoder=mock_geocoder,
        pinner=mock_pinner,
    )

    item = await pipeline.process_url("https://www.xiaohongshu.com/explore/note789")

    assert item.location.place_name == "武康大楼"
    assert item.google_place.place_id == "wukang_123"
    assert item.pinned_status == "Success"
    assert "Pinned to Google My Maps" in item.pinned_info
