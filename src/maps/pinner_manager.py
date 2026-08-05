"""
Pinner Manager unifying pinning strategies (Sheets, KML, Playwright, None).
"""

from typing import Tuple
from config import config
from src.models.place import ProcessedMapItem
from src.maps.pinner_sheets import GoogleSheetsPinner
from src.maps.pinner_kml import KMLPinner
from src.maps.pinner_playwright import PlaywrightPinner


class PinnerManager:
    """Manager for pinning place items using configured strategy."""

    def __init__(self, strategy: str = None):
        self.strategy = strategy or config.PINNER_STRATEGY
        self.sheets_pinner = GoogleSheetsPinner()
        self.kml_pinner = KMLPinner()
        self.playwright_pinner = PlaywrightPinner()

    async def pin(self, item: ProcessedMapItem) -> Tuple[bool, str]:
        """
        Execute pinning based on configured strategy.
        Returns (success: bool, info_message: str).
        """
        if self.strategy == "sheets":
            return await self.sheets_pinner.pin_place(item)
        elif self.strategy == "kml":
            return await self.kml_pinner.pin_place(item)
        elif self.strategy == "playwright":
            return await self.playwright_pinner.pin_place(item)
        elif self.strategy == "none":
            return True, "Pinning strategy disabled ('none')."
        else:
            # Fallback to KML if unknown
            return await self.kml_pinner.pin_place(item)
