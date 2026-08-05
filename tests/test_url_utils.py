"""
Unit tests for Xiaohongshu URL extraction and resolution utilities.
"""

import pytest
from src.scrapers.url_utils import extract_xhs_urls, extract_note_id, resolve_xhs_url


def test_extract_xhs_urls():
    # Test 1: Single short link embedded in Xiaohongshu mobile share text
    text1 = "12 复制打开小红书，查看精彩笔记！http://xhslink.com/a/1a2b3c4d 了解更多"
    urls1 = extract_xhs_urls(text1)
    assert len(urls1) == 1
    assert urls1[0] == "http://xhslink.com/a/1a2b3c4d"

    # Test 2: Standard web URL
    text2 = "Check out this place https://www.xiaohongshu.com/explore/64f1a2b3000000001a2b3c4d!"
    urls2 = extract_xhs_urls(text2)
    assert len(urls2) == 1
    assert urls2[0] == "https://www.xiaohongshu.com/explore/64f1a2b3000000001a2b3c4d"

    # Test 3: Multiple links in same text
    text3 = "Link 1: https://xhslink.com/A1B2C3 and Link 2: https://www.xiaohongshu.com/discovery/item/987654321"
    urls3 = extract_xhs_urls(text3)
    assert len(urls3) == 2

    # Test 4: No URL in text
    assert extract_xhs_urls("Just normal text without any links") == []


def test_extract_note_id():
    url1 = "https://www.xiaohongshu.com/explore/64f1a2b3000000001a2b3c4d"
    assert extract_note_id(url1) == "64f1a2b3000000001a2b3c4d"

    url2 = "https://www.xiaohongshu.com/discovery/item/abc123xyz"
    assert extract_note_id(url2) == "abc123xyz"

    url3 = "https://xhslink.com/a/123"
    assert extract_note_id(url3) is None


@pytest.mark.asyncio
async def test_resolve_xhs_url_fallback():
    # Standard URL should be returned directly
    url = "https://www.xiaohongshu.com/explore/123456"
    resolved = await resolve_xhs_url(url)
    assert resolved == url
