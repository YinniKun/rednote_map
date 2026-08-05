"""
Google Sheets Pinner Strategy.
Appends place records to a Google Sheet connected live to Google My Maps.
"""

from datetime import datetime
from typing import Optional, Tuple
import gspread
from google.oauth2.service_account import Credentials
from config import config
from src.models.place import ProcessedMapItem


class GoogleSheetsPinner:
    """Pins places by adding rows to a Google Sheet (synced with Google My Maps)."""

    def __init__(self, sheet_id: Optional[str] = None, service_account_file: Optional[str] = None):
        self.sheet_id = sheet_id or config.GOOGLE_SHEETS_ID
        self.service_account_file = service_account_file or config.GOOGLE_SERVICE_ACCOUNT_FILE
        self._gc = None

    def _get_client(self):
        if self._gc is None and self.service_account_file:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            try:
                creds = Credentials.from_service_account_file(self.service_account_file, scopes=scopes)
                self._gc = gspread.authorize(creds)
            except Exception:
                pass
        return self._gc

    async def pin_place(self, item: ProcessedMapItem) -> Tuple[bool, str]:
        """
        Append place data to Google Sheet.
        Columns: [Place Name, Category, Address, Latitude, Longitude, Summary, Xiaohongshu Link, Date Added]
        """
        if not self.sheet_id:
            return False, "Google Sheets ID not configured in .env (GOOGLE_SHEETS_ID)"

        gc = self._get_client()
        if not gc:
            return False, f"Failed to authorize Google Service Account using file: {self.service_account_file}"

        try:
            sh = gc.open_by_key(self.sheet_id)
            worksheet = sh.get_worksheet(0) or sh.sheet1

            # Ensure headers exist
            headers = ["Place Name", "Category", "Address", "Latitude", "Longitude", "Summary", "Xiaohongshu Link", "Date Added"]
            existing_headers = worksheet.row_values(1)
            if not existing_headers:
                worksheet.append_row(headers)

            lat = item.google_place.latitude if item.google_place else 0.0
            lng = item.google_place.longitude if item.google_place else 0.0
            address = item.google_place.formatted_address if item.google_place else (item.location.city_or_district or "")
            maps_link = item.google_place.google_maps_url if item.google_place else ""

            row = [
                item.location.place_name,
                item.location.category,
                address,
                lat,
                lng,
                item.location.summary,
                item.note.url,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]

            worksheet.append_row(row)
            return True, "📍 Pinned to Google My Maps via Google Sheets sync!"
        except Exception as e:
            return False, f"Google Sheets append error: {str(e)}"
