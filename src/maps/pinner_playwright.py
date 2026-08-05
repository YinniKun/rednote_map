"""
Optional Playwright Browser Pinner Strategy.
Automates saving places directly to personal Google Maps Saved Lists (Starred / Want to Go)
using Playwright browser with saved session context.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from config import config
from src.models.place import ProcessedMapItem


class PlaywrightPinner:
    """Pins places directly on Google Maps UI using Playwright browser automation."""

    def __init__(self, session_path: Optional[str] = None):
        self.session_path = Path(session_path or os.getenv("PLAYWRIGHT_SESSION_FILE", "google_session.json"))

    async def pin_place(self, item: ProcessedMapItem) -> Tuple[bool, str]:
        """
        Open Google Maps URL in headless Playwright browser with saved Google login session,
        and click 'Save' -> 'Want to go' / 'Starred'.
        """
        if not item.google_place or not item.google_place.google_maps_url:
            return False, "No Google Maps URL available for browser pinning."

        if not self.session_path.exists():
            return False, f"Playwright Google session file not found at {self.session_path}. Run login script first."

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(storage_state=str(self.session_path))
                page = await context.new_page()

                await page.goto(item.google_place.google_maps_url, timeout=30000)
                await page.wait_for_load_state("networkidle")

                # Try clicking Save button on Google Maps Place details panel
                save_btn = page.locator("button[data-tooltip='保存'], button[aria-label*='Save'], button[data-tooltip='Save']")
                if await save_btn.count() > 0:
                    await save_btn.first.click()
                    await page.wait_for_timeout(1000)

                    # Click 'Want to go' or 'Starred' list item
                    want_to_go = page.locator("text='想去' , text='Want to go' , text='收藏'")
                    if await want_to_go.count() > 0:
                        await want_to_go.first.click()
                        await page.wait_for_timeout(1000)
                        await browser.close()
                        return True, "📍 Saved to Google Maps personal list via Playwright automation!"

                await browser.close()
                return False, "Could not locate 'Save' button on Google Maps page."
        except Exception as e:
            return False, f"Playwright browser error: {str(e)}"
