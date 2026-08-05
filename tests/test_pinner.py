"""
Unit tests for Google Maps pinning strategies (KML & PinnerManager).
"""

import pytest
from pathlib import Path
from src.models.place import NoteData, ExtractedLocation, GooglePlaceDetails, ProcessedMapItem
from src.maps.pinner_kml import KMLPinner
from src.maps.pinner_manager import PinnerManager


@pytest.mark.asyncio
async def test_kml_pinner(tmp_path):
    test_kml_file = tmp_path / "test_saved_places.kml"
    pinner = KMLPinner(kml_filepath=str(test_kml_file))

    item = ProcessedMapItem(
        note=NoteData(url="https://www.xiaohongshu.com/explore/note123", note_id="note123", title="BRUT CAFE"),
        location=ExtractedLocation(place_name="BRUT CAFE", category="Cafe", search_query="BRUT CAFE", summary="Great cafe"),
        google_place=GooglePlaceDetails(
            place_id="p123",
            name="BRUT CAFE",
            formatted_address="Yuyuan Road, Shanghai",
            latitude=31.22,
            longitude=121.43,
            google_maps_url="https://google.com/maps"
        )
    )

    success, msg = await pinner.pin_place(item)
    assert success is True
    assert test_kml_file.exists()

    content = test_kml_file.read_text(encoding="utf-8")
    assert "BRUT CAFE" in content
    assert "121.43,31.22,0" in content


@pytest.mark.asyncio
async def test_pinner_manager_none():
    manager = PinnerManager(strategy="none")
    item = ProcessedMapItem(
        note=NoteData(url="https://xhslink.com/123", note_id="123"),
        location=ExtractedLocation(place_name="Spot", search_query="Spot", summary="Summary"),
    )

    success, msg = await manager.pin(item)
    assert success is True
    assert "disabled" in msg
