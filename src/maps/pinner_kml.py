"""
KML / GeoJSON Pinner Strategy.
Appends place records into a local KML map file for direct Google My Maps import.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from xml.etree import ElementTree as ET
from config import config
from src.models.place import ProcessedMapItem


class KMLPinner:
    """Pins places by updating a local KML map file."""

    def __init__(self, kml_filepath: Optional[str] = None):
        self.kml_path = Path(kml_filepath or config.KML_OUTPUT_FILE)

    async def pin_place(self, item: ProcessedMapItem) -> Tuple[bool, str]:
        """Add placemark to KML file."""
        try:
            place_name = item.location.place_name
            lat = item.google_place.latitude if item.google_place else 0.0
            lng = item.google_place.longitude if item.google_place else 0.0
            summary = item.location.summary
            category = item.location.category
            xhs_url = item.note.url

            # Description HTML for KML popup
            description = f"Category: {category}<br/>Summary: {summary}<br/>XHS: <a href='{xhs_url}'>Link</a>"

            self._add_to_kml(place_name, lat, lng, description)
            return True, f"📍 Added to local KML file ({self.kml_path.name})"
        except Exception as e:
            return False, f"Failed to update KML: {str(e)}"

    def _add_to_kml(self, name: str, lat: float, lng: float, description: str):
        """Parse or create KML XML root and append new Placemark."""
        if not self.kml_path.exists() or self.kml_path.stat().st_size == 0:
            kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Xiaohongshu Pinned Places</name>
    <description>Places extracted from Xiaohongshu notes</description>
  </Document>
</kml>"""
            self.kml_path.write_text(kml_content, encoding="utf-8")

        # Parse existing XML
        tree = ET.parse(self.kml_path)
        root = tree.getroot()
        namespace = "{http://www.opengis.net/kml/2.2}"

        doc = root.find(f"{namespace}Document")
        if doc is None:
            doc = ET.SubElement(root, f"{namespace}Document")

        # Create new Placemark
        placemark = ET.SubElement(doc, f"{namespace}Placemark")
        name_elem = ET.SubElement(placemark, f"{namespace}name")
        name_elem.text = name

        desc_elem = ET.SubElement(placemark, f"{namespace}description")
        desc_elem.text = description

        point = ET.SubElement(placemark, f"{namespace}Point")
        coords = ET.SubElement(point, f"{namespace}coordinates")
        coords.text = f"{lng},{lat},0"

        # Register namespace prefix for clean output
        ET.register_namespace("", "http://www.opengis.net/kml/2.2")
        tree.write(self.kml_path, encoding="utf-8", xml_declaration=True)
