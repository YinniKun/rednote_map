"""
Base class interface for LLM Location Extractors.
"""

from abc import ABC, abstractmethod
from src.models.place import NoteData, ExtractedLocation


class BaseLLMExtractor(ABC):
    """Abstract interface for LLM location extraction."""

    @abstractmethod
    async def extract_location(self, note: NoteData) -> ExtractedLocation:
        """
        Analyze Xiaohongshu note content and extract place details.

        :param note: NoteData containing note title, description, tags, POI.
        :return: ExtractedLocation containing place_name, city, search_query, category, summary.
        """
        pass
