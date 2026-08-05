"""
Utilities for Xiaohongshu URL matching and short link resolution.
"""

import re
from typing import List, Optional
import httpx
from config import config

# Regex patterns for Xiaohongshu links (supports .com, .cn, .net)
XHS_URL_REGEX = re.compile(
    r"https?://(?:www\.)?(?:xhslink\.(?:com|cn|net)/[A-Za-z0-9/_-]+|(?:xiaohongshu|rednote)\.(?:com|cn)/(?:explore|discovery/item)/[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)


def extract_xhs_urls(text: str) -> List[str]:
    """
    Extract all Xiaohongshu URLs from message text.
    Handles raw share text from mobile app containing URLs embedded in Chinese text.
    """
    if not text:
        return []
    matches = XHS_URL_REGEX.findall(text)
    # Deduplicate while maintaining order
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


async def resolve_xhs_url(url: str) -> str:
    """
    Follow HTTP redirects if the URL is a short link (xhslink.com / xhslink.cn).
    Returns the resolved canonical Xiaohongshu URL.
    """
    if "xhslink" not in url.lower():
        return url

    headers = {"User-Agent": config.USER_AGENT}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resolved_url = str(resp.url)
            return resolved_url
    except Exception as e:
        # If redirect resolution fails, return original URL
        return url


def extract_note_id(url: str) -> Optional[str]:
    """
    Extract note ID from canonical Xiaohongshu URL.
    Example: https://www.xiaohongshu.com/explore/64f1a2b3000000001a2b3c4d -> 64f1a2b3000000001a2b3c4d
    """
    match = re.search(r"/(?:explore|discovery/item)/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None
