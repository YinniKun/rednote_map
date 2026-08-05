"""
Base class interface for LLM Location Extractors.
"""

from abc import ABC, abstractmethod
from typing import List
from src.models.place import NoteData, ExtractedLocation


class BaseLLMExtractor(ABC):
    """Abstract interface for LLM location extraction."""

    @abstractmethod
    async def extract_location(self, note: NoteData) -> ExtractedLocation:
        """Analyze Xiaohongshu note content and extract primary place detail."""
        pass

    @abstractmethod
    async def extract_locations(self, note: NoteData) -> List[ExtractedLocation]:
        """Analyze Xiaohongshu note content and extract ALL mentioned places (1 to 5 spots)."""
        pass
