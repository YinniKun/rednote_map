"""
Discord Embed Formatter for Xiaohongshu Map items.
Creates visually stunning Discord Embed cards for single or multiple extracted locations.
"""

from typing import List
import discord
from src.models.place import ProcessedMapItem, ProcessedResult

# Color mapping by place category
CATEGORY_COLORS = {
    "Cafe": 0xD97706,        # Warm amber / Coffee color
    "Restaurant": 0xEF4444,  # Bright red / Food color
    "Bakery": 0xF59E0B,      # Golden yellow
    "Sightseeing": 0x10B981, # Emerald green
    "Park": 0x10B981,       # Green
    "Bar": 0x8B5CF6,        # Purple
    "Hotel": 0x3B82F6,      # Blue
    "Shopping": 0xEC4899,   # Pink
    "Other": 0x6B7280,      # Gray
}


def build_result_embeds(result: ProcessedResult) -> List[discord.Embed]:
    """
    Build Discord Embed cards for all places in ProcessedResult.
    Outputs a dedicated Embed card for each extracted place so NO place is omitted.
    """
    if not result.items:
        embed = discord.Embed(
            title="📍 小红书地点提取结果",
            description="未能提取到具体地点信息，请检查笔记内容。",
            color=0xEF4444
        )
        return [embed]

    embeds = []
    total_spots = len(result.items)

    for idx, item in enumerate(result.items, 1):
        category = item.location.category or "Other"
        color = CATEGORY_COLORS.get(category, 0x3B82F6)

        # Title includes spot number if multiple spots
        spot_prefix = f"📍 [{idx}/{total_spots}] " if total_spots > 1 else "📍 "
        title = f"{spot_prefix}{item.location.place_name}"

        embed = discord.Embed(
            title=title,
            description=item.location.summary,
            color=color,
        )

        address_val = item.google_place.formatted_address if item.google_place else (item.location.city_or_district or "N/A")
        embed.add_field(name="🏙️ 所在地区/地址", value=f"`{address_val}`", inline=False)
        embed.add_field(name="🏷️ 分类", value=f"`{category}`", inline=True)

        if item.google_place and item.google_place.rating:
            ratings_str = f"⭐ {item.google_place.rating}"
            if item.google_place.user_ratings_total:
                ratings_str += f" ({item.google_place.user_ratings_total} 评价)"
            embed.add_field(name="⭐ Google 评分", value=ratings_str, inline=True)

        # Direct Mobile Google Maps Link inside Embed field for max accessibility
        if item.google_place and item.google_place.google_maps_url:
            embed.add_field(
                name="🗺️ Google 地图导航/保存链接",
                value=f"[📱 点击在 Google 地图打开并保存]({item.google_place.google_maps_url})",
                inline=False
            )

        note_info = f"[{result.note.title or '查看小红书原笔记'}]({result.note.url})"
        if result.note.author:
            note_info += f" by {result.note.author}"
        embed.add_field(name="📕 小红书来源", value=note_info, inline=False)

        if result.note.image_urls:
            embed.set_thumbnail(url=result.note.image_urls[0])

        pin_badge = f"标注状态: {item.pinned_info or item.pinned_status}"
        embed.set_footer(text=f"RedNote Maps Bot • 地点 {idx}/{total_spots} • {pin_badge}")

        embeds.append(embed)

    return embeds


def build_result_embed(result: ProcessedResult) -> discord.Embed:
    """Fallback single embed generator."""
    embeds = build_result_embeds(result)
    return embeds[0]


def build_place_embed(item: ProcessedMapItem) -> discord.Embed:
    """Build a rich Discord Embed card for a single processed place."""
    result = ProcessedResult(note=item.note, items=[item])
    return build_result_embeds(result)[0]


def build_result_view(result: ProcessedResult) -> discord.ui.View:
    """Build interactive action buttons for ProcessedResult (supports all spots)."""
    view = discord.ui.View(timeout=None)

    # Add Google Maps mobile buttons for up to 4 places
    for idx, item in enumerate(result.items[:4], 1):
        if item.google_place and item.google_place.google_maps_url:
            label = f"地图: {item.location.place_name[:12]}" if len(result.items) > 1 else "在 Google 地图查看"
            view.add_item(
                discord.ui.Button(
                    label=label,
                    url=item.google_place.google_maps_url,
                    style=discord.ButtonStyle.link,
                    emoji="🗺️"
                )
            )

    # Button: Open original Xiaohongshu note
    view.add_item(
        discord.ui.Button(
            label="打开小红书笔记",
            url=result.note.url,
            style=discord.ButtonStyle.link,
            emoji="📕"
        )
    )

    return view


def build_action_view(item: ProcessedMapItem) -> discord.ui.View:
    """Build interactive action buttons for single ProcessedMapItem."""
    result = ProcessedResult(note=item.note, items=[item])
    return build_result_view(result)
