"""
Discord Embed Formatter for Xiaohongshu Map items.
Creates visually stunning Discord Embed cards for single or multiple extracted locations.
"""

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


def build_result_embed(result: ProcessedResult) -> discord.Embed:
    """Build a rich Discord Embed card from ProcessedResult (single or multi-place)."""
    if not result.items:
        embed = discord.Embed(
            title="📍 小红书地点提取结果",
            description="未能提取到具体地点信息，请检查笔记内容。",
            color=0xEF4444
        )
        return embed

    # If single item, use detailed single place embed
    if len(result.items) == 1:
        return build_place_embed(result.items[0])

    # If multiple items in 1 note (e.g.合集推荐)
    note = result.note
    primary_category = result.items[0].location.category or "Other"
    color = CATEGORY_COLORS.get(primary_category, 0x3B82F6)

    title = f"📍 笔记共推荐了 {len(result.items)} 个打卡地点"
    embed = discord.Embed(
        title=title,
        description=f"**小红书笔记**: [{note.title or '查看原笔记'}]({note.url})",
        color=color
    )

    for idx, item in enumerate(result.items, 1):
        loc = item.location
        gp = item.google_place
        address = gp.formatted_address if gp else (loc.city_or_district or "地址未检索到")
        maps_link = f" [🗺️在地图打开]({gp.google_maps_url})" if gp and gp.google_maps_url else ""
        
        field_name = f"{idx}. {loc.place_name} ({loc.category})"
        field_val = f"📍 地址: `{address}`\n💡 简介: {loc.summary}{maps_link}"
        embed.add_field(name=field_name, value=field_val, inline=False)

    if note.image_urls:
        embed.set_thumbnail(url=note.image_urls[0])

    pinned_summary = f"已完成 {len(result.items)} 个地点的标注"
    embed.set_footer(text=f"RedNote Maps Bot • {pinned_summary}")
    return embed


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


def build_result_view(result: ProcessedResult) -> discord.ui.View:
    """Build interactive action buttons for ProcessedResult."""
    view = discord.ui.View(timeout=None)

    # Add Google Maps links for items (up to 3 buttons due to Discord view limits)
    for idx, item in enumerate(result.items[:3], 1):
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
    view = discord.ui.View(timeout=None)

    if item.google_place and item.google_place.google_maps_url:
        view.add_item(
            discord.ui.Button(
                label="在 Google 地图查看",
                url=item.google_place.google_maps_url,
                style=discord.ButtonStyle.link,
                emoji="🗺️"
            )
        )

    view.add_item(
        discord.ui.Button(
            label="打开小红书笔记",
            url=item.note.url,
            style=discord.ButtonStyle.link,
            emoji="📕"
        )
    )

    return view
