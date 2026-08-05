"""
End-to-end processing pipeline for Xiaohongshu notes.
Orchestrates: Scraper -> LLM Extractor -> Google Maps Geocoder -> Pinner.
Supports multi-place extraction per note.
"""

from typing import Optional, List
from src.scrapers.xhs_parser import XhsParser
from src.llm.openai_extractor import OpenAIExtractor
from src.maps.geocoder import GoogleMapsGeocoder
from src.maps.pinner_manager import PinnerManager
from src.models.place import (
    ProcessedResult,
    ProcessedMapItem,
    NoteData,
    ExtractedLocation,
    GooglePlaceDetails,
)


class ProcessPipeline:
    """Core Processing Pipeline."""

    def __init__(
        self,
        parser: Optional[XhsParser] = None,
        extractor: Optional[OpenAIExtractor] = None,
        geocoder: Optional[GoogleMapsGeocoder] = None,
        pinner: Optional[PinnerManager] = None,
    ):
        self.parser = parser or XhsParser()
        self.extractor = extractor or OpenAIExtractor()
        self.geocoder = geocoder or GoogleMapsGeocoder()
        self.pinner = pinner or PinnerManager()

    async def process_url(self, raw_url: str, raw_share_text: Optional[str] = None) -> ProcessedResult:
        """
        Execute the full pipeline for a Xiaohongshu link:
        1. Fetch & parse Xiaohongshu note data (using share text fallback if needed)
        2. Analyze note content using LLM to extract all mentioned places (1 to 5 spots)
        3. Search Google Maps for place details & coordinates for each spot
        4. Pin each location to Google Maps account (Sheets sync / KML)
        """
        # Step 1: Scrape & Parse Note Data
        note_data: NoteData = await self.parser.parse(raw_url, raw_share_text=raw_share_text)

        # Step 2: LLM Location & Info Extraction (Supports multiple places in 1 note)
        extracted_locations: List[ExtractedLocation] = await self.extractor.extract_locations(note_data)

        items: List[ProcessedMapItem] = []

        # Step 3 & 4: Process each extracted location
        for loc in extracted_locations:
            google_place: Optional[GooglePlaceDetails] = await self.geocoder.search_place(loc)

            item = ProcessedMapItem(
                note=note_data,
                location=loc,
                google_place=google_place,
                pinned_status="Pending"
            )

            success, info_msg = await self.pinner.pin(item)
            item.pinned_status = "Success" if success else "Failed"
            item.pinned_info = info_msg
            items.append(item)

        return ProcessedResult(note=note_data, items=items)
