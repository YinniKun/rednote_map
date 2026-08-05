"""
Unit tests for Google Maps geocoding and fallback place generation.
"""

import pytest
from src.models.place import ExtractedLocation
from src.maps.geocoder import GoogleMapsGeocoder


def test_fallback_place_generation():
    geocoder = GoogleMapsGeocoder(api_key="")  # No API key triggers fallback
    loc = ExtractedLocation(
        place_name="BRUT CAFE",
        city_or_district="上海市静安区愚园路",
        category="Cafe",
        search_query="BRUT CAFE Yuyuan Road Shanghai",
        summary="特色复古咖啡馆"
    )

    place = geocoder._generate_fallback_place(loc)
    assert place.name == "BRUT CAFE"
    assert place.formatted_address == "上海市静安区愚园路"
    assert "google.com/maps" in place.google_maps_url


@pytest.mark.asyncio
async def test_search_place_fallback_flow():
    geocoder = GoogleMapsGeocoder(api_key="")
    loc = ExtractedLocation(
        place_name="武康大楼",
        city_or_district="上海徐汇区淮海中路",
        category="Sightseeing",
        search_query="武康大楼 Shanghai",
        summary="上海著名历史建筑"
    )

    place = await geocoder.search_place(loc)
    assert place is not None
    assert place.name == "武康大楼"
