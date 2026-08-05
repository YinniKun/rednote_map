"""
Unit tests for Discord embed generation formatting.
"""

from src.models.place import NoteData, ExtractedLocation, GooglePlaceDetails, ProcessedMapItem, ProcessedResult
from src.bot.formatters import build_place_embed, build_action_view, build_result_embed, build_result_view


def test_build_place_embed():
    item = ProcessedMapItem(
        note=NoteData(
            url="https://www.xiaohongshu.com/explore/note123",
            note_id="note123",
            title="愚园路 BRUT CAFE",
            author="TravelBlogger",
            image_urls=["https://img.xhs.com/cafe.jpg"]
        ),
        location=ExtractedLocation(
            place_name="BRUT CAFE",
            city_or_district="上海市静安区愚园路",
            category="Cafe",
            search_query="BRUT CAFE Yuyuan Road Shanghai",
            summary="复古温馨咖啡馆，推荐鲜奶拿铁！"
        ),
        google_place=GooglePlaceDetails(
            place_id="brut_cafe_id",
            name="BRUT CAFE",
            formatted_address="123 Yuyuan Rd, Jing'an, Shanghai",
            latitude=31.222,
            longitude=121.433,
            google_maps_url="https://www.google.com/maps/place/?q=place_id:brut_cafe_id",
            rating=4.6,
            user_ratings_total=128
        ),
        pinned_status="Success",
        pinned_info="📍 Pinned to Google My Maps via Google Sheets sync!"
    )

    embed = build_place_embed(item)
    assert embed.title == "📍 BRUT CAFE"
    assert embed.description == "复古温馨咖啡馆，推荐鲜奶拿铁！"
    assert embed.color.value == 0xD97706  # Cafe color
    assert any("BRUT CAFE" in field.value or "TravelBlogger" in field.value for field in embed.fields)

    view = build_action_view(item)
    assert len(view.children) == 2  # 2 Link Buttons (Google Maps & XHS)


def test_build_multi_result_embed():
    note = NoteData(url="http://xhslink.cn/123", note_id="123", title="多伦多周边2个小镇")
    item1 = ProcessedMapItem(
        note=note,
        location=ExtractedLocation(place_name="Elora Town", category="Sightseeing", search_query="Elora", summary="Nice town"),
        google_place=GooglePlaceDetails(place_id="e1", name="Elora", formatted_address="Elora ON", latitude=43.6, longitude=-80.4, google_maps_url="https://maps.google.com/e1")
    )
    item2 = ProcessedMapItem(
        note=note,
        location=ExtractedLocation(place_name="Port Hope", category="Sightseeing", search_query="Port Hope", summary="Historic town"),
        google_place=GooglePlaceDetails(place_id="p1", name="Port Hope", formatted_address="Port Hope ON", latitude=43.9, longitude=-78.3, google_maps_url="https://maps.google.com/p1")
    )

    result = ProcessedResult(note=note, items=[item1, item2])
    embed = build_result_embed(result)

    assert "2 个打卡地点" in embed.title
    assert len(embed.fields) == 2
    assert "Elora Town" in embed.fields[0].name
    assert "Port Hope" in embed.fields[1].name

    view = build_result_view(result)
    assert len(view.children) == 3  # 2 Google Maps buttons + 1 XHS button
