"""
Data models for Note, Location, Google Place, and Combined Processed Map Item.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NoteData(BaseModel):
    """Raw extracted note data from Xiaohongshu."""
    url: str
    note_id: str
    title: str = ""
    desc: str = ""
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    poi_name: Optional[str] = None  # Location tag attached directly in Xiaohongshu if any
    image_urls: List[str] = Field(default_factory=list)


class ExtractedLocation(BaseModel):
    """Structured location information extracted by LLM from note content."""
    place_name: str = Field(description="Name of the restaurant, cafe, shop, attraction or spot")
    city_or_district: Optional[str] = Field(default=None, description="City, district, street, or region mentioned")
    category: str = Field(default="Attraction", description="Category: Cafe, Restaurant, Sightseeing, Bakery, Bar, Hotel, Shopping, etc.")
    search_query: str = Field(description="Optimized query string to search on Google Maps")
    summary: str = Field(description="1-2 sentence recommendation summary based on the note")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0")


class GooglePlaceDetails(BaseModel):
    """Details retrieved from Google Maps Places/Geocoding API."""
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    google_maps_url: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None


class ProcessedMapItem(BaseModel):
    """Combined object ready for Discord notification and Google Maps Pinning."""
    note: NoteData
    location: ExtractedLocation
    google_place: Optional[GooglePlaceDetails] = None
    pinned_status: str = "Pending"  # "Success", "Failed", "Skipped", etc.
    pinned_info: Optional[str] = None
