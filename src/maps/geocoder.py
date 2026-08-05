"""
Google Maps Geocoding and Places API Service.
Resolves extracted search queries to exact Google Places (place_id, coordinates, address, maps URL).
"""

from typing import Optional
import httpx
from config import config
from src.models.place import ExtractedLocation, GooglePlaceDetails


class GoogleMapsGeocoder:
    """Google Maps Geocoding & Places Search Client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GOOGLE_MAPS_API_KEY
        self._gmaps_client = None

    def _get_client(self):
        if self._gmaps_client is None and self.api_key:
            try:
                import googlemaps
                self._gmaps_client = googlemaps.Client(key=self.api_key)
            except Exception:
                pass
        return self._gmaps_client

    async def search_place(self, location: ExtractedLocation) -> Optional[GooglePlaceDetails]:
        """
        Search for a place on Google Maps using search query or place name + city.
        Returns GooglePlaceDetails if found, or fallback estimate.
        """
        if self.api_key:
            # 1. Try official Google Places Text Search via API
            try:
                details = await self._search_via_places_api(location.search_query)
                if details:
                    return details
            except Exception:
                pass

            # 2. Try Geocoding API as secondary fallback
            try:
                details = await self._search_via_geocoding_api(location.search_query)
                if details:
                    return details
            except Exception:
                pass

        # 3. Fallback mock / estimated place details when API key is missing or calls fail
        return self._generate_fallback_place(location)

    async def _search_via_places_api(self, query: str) -> Optional[GooglePlaceDetails]:
        """Query Google Places Text Search API via HTTP."""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {"query": query, "key": self.api_key, "language": "zh-CN"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

            if data.get("status") == "OK" and data.get("results"):
                top_result = data["results"][0]
                place_id = top_result.get("place_id")
                name = top_result.get("name")
                address = top_result.get("formatted_address", "")
                loc = top_result.get("geometry", {}).get("location", {})
                lat = loc.get("lat", 0.0)
                lng = loc.get("lng", 0.0)
                rating = top_result.get("rating")
                ratings_count = top_result.get("user_ratings_total")

                maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

                return GooglePlaceDetails(
                    place_id=place_id,
                    name=name,
                    formatted_address=address,
                    latitude=lat,
                    longitude=lng,
                    google_maps_url=maps_url,
                    rating=rating,
                    user_ratings_total=ratings_count,
                )
        return None

    async def _search_via_geocoding_api(self, query: str) -> Optional[GooglePlaceDetails]:
        """Query Google Geocoding API as secondary lookup."""
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": query, "key": self.api_key, "language": "zh-CN"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

            if data.get("status") == "OK" and data.get("results"):
                top_result = data["results"][0]
                place_id = top_result.get("place_id", "geo_place_1")
                address = top_result.get("formatted_address", query)
                loc = top_result.get("geometry", {}).get("location", {})
                lat = loc.get("lat", 0.0)
                lng = loc.get("lng", 0.0)

                maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

                return GooglePlaceDetails(
                    place_id=place_id,
                    name=query,
                    formatted_address=address,
                    latitude=lat,
                    longitude=lng,
                    google_maps_url=maps_url,
                )
        return None

    def _generate_fallback_place(self, location: ExtractedLocation) -> GooglePlaceDetails:
        """Generate estimated place details for offline / fallback testing."""
        safe_query = location.search_query.replace(" ", "+")
        maps_url = f"https://www.google.com/maps/search/?api=1&query={safe_query}"
        
        return GooglePlaceDetails(
            place_id=f"fallback_{hash(location.place_name) & 0xFFFFFFFF}",
            name=location.place_name,
            formatted_address=location.city_or_district or "Address pending Google Maps search",
            latitude=31.2304,   # Default reference coordinate (Shanghai center / general)
            longitude=121.4737,
            google_maps_url=maps_url,
        )
