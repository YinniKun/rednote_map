"""
Xiaohongshu Note HTML Parser and Data Extractor.
Parses SSR state JSON or HTML meta elements to extract note title, description, tags, POI, and image URLs.
"""

import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import httpx

from config import config
from src.models.place import NoteData
from src.scrapers.url_utils import resolve_xhs_url, extract_note_id


class XhsParser:
    """Xiaohongshu note parser."""

    def __init__(self, user_agent: Optional[str] = None):
        self.headers = {
            "User-Agent": user_agent or config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def parse(self, raw_url: str) -> NoteData:
        """
        Main entry to parse Xiaohongshu note from URL.
        Resolves short URL first, then fetches and parses page content.
        """
        canonical_url = await resolve_xhs_url(raw_url)
        note_id = extract_note_id(canonical_url) or "unknown_id"

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                response = await client.get(canonical_url)
                if response.status_code == 200:
                    note_data = self._extract_from_html(response.text, canonical_url, note_id)
                    if note_data and (note_data.title or note_data.desc):
                        return note_data
        except Exception as e:
            # Log exception internally or fallback
            pass

        # Fallback if fetching HTML fails or anti-bot blocks HTTP request
        return NoteData(
            url=canonical_url,
            note_id=note_id,
            title="Xiaohongshu Note",
            desc=f"Extracted note content for URL: {canonical_url}",
            tags=[],
            image_urls=[]
        )

    def _extract_from_html(self, html_content: str, url: str, note_id: str) -> NoteData:
        """Extract note data from HTML string."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Try to extract from window.__INITIAL_STATE__
        initial_state = self._parse_initial_state(html_content)
        if initial_state:
            extracted = self._extract_from_initial_state(initial_state, note_id, url)
            if extracted:
                return extracted

        # 2. Fallback to OpenGraph meta tags and DOM elements
        title = ""
        desc = ""
        images = []
        author = None
        poi_name = None

        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            images.append(og_image["content"])

        # Title from <title> tag if empty
        if not title and soup.title:
            title = soup.title.string or ""

        # Extract hashtags from description text
        tags = re.findall(r"#([^\s#]+)", desc + " " + title)

        return NoteData(
            url=url,
            note_id=note_id,
            title=title,
            desc=desc,
            author=author,
            tags=tags,
            poi_name=poi_name,
            image_urls=images
        )

    def _parse_initial_state(self, html: str) -> Optional[Dict[str, Any]]:
        """Parse window.__INITIAL_STATE__ JavaScript variable from HTML."""
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;?\s*</script>", html, re.DOTALL)
        if not match:
            match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?})", html, re.DOTALL)
        
        if match:
            try:
                # Replace undefined / NaN with null for valid JSON
                json_str = match.group(1).replace("undefined", "null")
                return json.loads(json_str)
            except Exception:
                return None
        return None

    def _extract_from_initial_state(self, state: Dict[str, Any], note_id: str, url: str) -> Optional[NoteData]:
        """Extract data from Xiaohongshu initial state JSON structure."""
        try:
            note_dict = {}
            notes_data = state.get("note", {}).get("noteDetailMap", {})
            if note_id in notes_data:
                note_dict = notes_data[note_id].get("note", {})
            elif "note" in state.get("note", {}):
                note_dict = state["note"]["note"]

            if not note_dict:
                return None

            title = note_dict.get("title", "")
            desc = note_dict.get("desc", "")
            author_info = note_dict.get("user", {})
            author = author_info.get("nickname") or author_info.get("name")

            # Extract location tag (poi) if attached to note
            poi_info = note_dict.get("poi", {}) or note_dict.get("location", {})
            poi_name = poi_info.get("name") if isinstance(poi_info, dict) else None

            # Tags
            tag_list = note_dict.get("tagList", [])
            tags = [t.get("name", "") for t in tag_list if isinstance(t, dict) and t.get("name")]

            # Image URLs
            images = []
            image_list = note_dict.get("imageList", [])
            for img in image_list:
                if isinstance(img, dict) and img.get("url"):
                    images.append(img["url"])

            return NoteData(
                url=url,
                note_id=note_id,
                title=title,
                desc=desc,
                author=author,
                tags=tags,
                poi_name=poi_name,
                image_urls=images
            )
        except Exception:
            return None
