"""
Discord Embed Formatter for Xiaohongshu Map items.
Creates visually stunning Discord Embed cards with category colors, metadata, and quick action buttons.
"""

import discord
from src.models.place import ProcessedMapItem

# Color mapping by place category
CATEGORY_COLORS = {
    "Cafe": 0xD97706,        # Warm amber / Coffee color
    "Restaurant": 0xEF4444,  # Bright red / Food color
    "Bakery": 0xF59E0B,      # Golden yellow
    "Sightseeing": 0x10B981, # Emerald green
    "Bar": 0x8B5CF6,        # Purple
    "Hotel": 0x3B82F6,      # Blue
    "Shopping": 0xEC4899,   # Pink
    "Other": 0x6B7280,      # Gray
}


def build_place_embed(item: ProcessedMapItem) -> discord.Embed:
    """Build a rich Discord Embed card for a processed Xiaohongshu place."""
    category = item.location.category or "Other"
    color = CATEGORY_COLORS.get(category, 0x3B82F6)

    title = f"📍 {item.location.place_name}"
    embed = discord.Embed(
        title=title,
        description=item.location.summary,
        color=color,
    )

    # Location details
    address_val = item.google_place.formatted_address if item.google_place else (item.location.city_or_district or "N/A")
    embed.add_field(name="🏙️ 所在地区/地址", value=f"`{address_val}`", inline=False)
    embed.add_field(name="🏷️ 分类", value=f"`{category}`", inline=True)

    if item.google_place and item.google_place.rating:
        ratings_str = f"⭐ {item.google_place.rating}"
        if item.google_place.user_ratings_total:
            ratings_str += f" ({item.google_place.user_ratings_total} 评价)"
        embed.add_field(name="⭐ Google 评分", value=ratings_str, inline=True)

    # Note information
    note_info = f"[{item.note.title or '查看小红书原笔记'}]({item.note.url})"
    if item.note.author:
        note_info += f" by {item.note.author}"
    embed.add_field(name="📕 小红书来源", value=note_info, inline=False)

    # Thumbnail image from Xiaohongshu note if available
    if item.note.image_urls:
        embed.set_thumbnail(url=item.note.image_urls[0])

    # Footer with pin status
    pin_badge = f"📍 标注状态: {item.pinned_info or item.pinned_status}"
    embed.set_footer(text=f"RedNote Maps Bot • {pin_badge}")

    return embed


def build_action_view(item: ProcessedMapItem) -> discord.ui.View:
    """Build interactive action buttons (Google Maps Link & Xiaohongshu Link)."""
    view = discord.ui.View(timeout=None)

    # Button 1: Open in Google Maps
    if item.google_place and item.google_place.google_maps_url:
        view.add_item(
            discord.ui.Button(
                label="在 Google 地图查看",
                url=item.google_place.google_maps_url,
                style=discord.ButtonStyle.link,
                emoji="🗺️"
            )
        )

    # Button 2: Open original Xiaohongshu note
    view.add_item(
        discord.ui.Button(
            label="打开小红书笔记",
            url=item.note.url,
            style=discord.ButtonStyle.link,
            emoji="📕"
        )
    )

    return view
