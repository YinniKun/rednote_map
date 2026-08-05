"""
End-to-end processing pipeline for Xiaohongshu notes.
Orchestrates: Scraper -> LLM Extractor -> Google Maps Geocoder -> Pinner.
"""

from typing import Optional
from src.scrapers.xhs_parser import XhsParser
from src.llm.openai_extractor import OpenAIExtractor
from src.maps.geocoder import GoogleMapsGeocoder
from src.maps.pinner_manager import PinnerManager
from src.models.place import ProcessedMapItem, NoteData, ExtractedLocation, GooglePlaceDetails


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

    async def process_url(self, raw_url: str) -> ProcessedMapItem:
        """
        Execute the full pipeline for a Xiaohongshu link:
        1. Fetch & parse Xiaohongshu note data
        2. Analyze note content using LLM to extract place & search query
        3. Search Google Maps for place details & coordinates
        4. Pin location to Google Maps account (Sheets sync / KML)
        """
        # Step 1: Scrape & Parse Note Data
        note_data: NoteData = await self.parser.parse(raw_url)

        # Step 2: LLM Location & Info Extraction
        extracted_loc: ExtractedLocation = await self.extractor.extract_location(note_data)

        # Step 3: Google Maps Place Lookup
        google_place: Optional[GooglePlaceDetails] = await self.geocoder.search_place(extracted_loc)

        # Create combined item
        item = ProcessedMapItem(
            note=note_data,
            location=extracted_loc,
            google_place=google_place,
            pinned_status="Pending"
        )

        # Step 4: Pin to Google Maps
        success, info_msg = await self.pinner.pin(item)
        item.pinned_status = "Success" if success else "Failed"
        item.pinned_info = info_msg

        return item
