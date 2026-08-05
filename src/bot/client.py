"""
Discord Bot Client Implementation.
Handles message listeners, slash commands, and interaction responses.
"""

import os
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

from config import config
from src.scrapers.url_utils import extract_xhs_urls
from src.services.pipeline import ProcessPipeline
from src.bot.formatters import build_result_embed, build_result_view


class RednoteMapBot(commands.Bot):
    """Discord Bot for auto-extracting Xiaohongshu places and marking Google Maps."""

    def __init__(self, pipeline: ProcessPipeline = None):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)
        self.pipeline = pipeline or ProcessPipeline()

    async def setup_hook(self):
        """Register and sync slash commands upon setup."""
        if config.DISCORD_GUILD_ID:
            guild = discord.Object(id=config.DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        """Callback when Discord Bot logs in successfully."""
        print(f"✅ Discord Bot logged in as {self.user} (ID: {self.user.id})")
        print(f"📍 Active Pin Strategy: {config.PINNER_STRATEGY}")
        if config.ALLOWED_CHANNEL_IDS:
            print(f"🔒 Allowed Channel IDs: {config.ALLOWED_CHANNEL_IDS}")
        else:
            print("🌐 Allowed Channels: ALL channels")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="小红书链接 | /analyze_xhs"
            )
        )


def create_bot(pipeline: ProcessPipeline = None) -> RednoteMapBot:
    """Factory to instantiate and set up Discord Bot with commands."""
    bot = RednoteMapBot(pipeline=pipeline)

    @bot.event
    async def on_message(message: discord.Message):
        # Ignore messages sent by bots
        if message.author.bot:
            return

        # Extract Xiaohongshu URLs from message
        urls = extract_xhs_urls(message.content)
        if not urls:
            await bot.process_commands(message)
            return

        # Check channel restriction if ALLOWED_CHANNEL_IDS is set
        if config.ALLOWED_CHANNEL_IDS and message.channel.id not in config.ALLOWED_CHANNEL_IDS:
            print(f"⚠️ Ignored XHS link in channel {message.channel.id} (Not in ALLOWED_CHANNEL_IDS)")
            await bot.process_commands(message)
            return

        # Process each detected Xiaohongshu link
        for url in urls:
            async with message.channel.typing():
                status_msg = await message.reply(f"🔍 收到小红书链接，AI 正在分析笔记内容并搜索 Google 地图定位...", mention_author=False)
                try:
                    # Pass full message text so LLM has rich context even if note webpage is anti-bot protected
                    result = await bot.pipeline.process_url(url, raw_share_text=message.content)
                    embed = build_result_embed(result)
                    view = build_result_view(result)
                    await status_msg.edit(content=None, embed=embed, view=view)
                except Exception as e:
                    await status_msg.edit(content=f"❌ 处理小红书链接失败: {str(e)}")

        await bot.process_commands(message)

    # --- Slash Commands ---

    @bot.tree.command(name="analyze_xhs", description="手动分析小红书笔记并标注到 Google 地图")
    @app_commands.describe(link="小红书笔记链接或分享文本")
    async def analyze_xhs(interaction: discord.Interaction, link: str):
        urls = extract_xhs_urls(link)
        if not urls:
            await interaction.response.send_message("❌ 未识别到有效的小红书链接，请检查输入的 URL。", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            result = await bot.pipeline.process_url(urls[0], raw_share_text=link)
            embed = build_result_embed(result)
            view = build_result_view(result)
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ 处理失败: {str(e)}")

    @bot.tree.command(name="map_status", description="查看 Bot 及 Google 地图标注配置状态")
    async def map_status(interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ Bot 运行状态与配置", color=0x3B82F6)
        embed.add_field(name="🤖 LLM 模型", value=f"`{config.LLM_PROVIDER}` ({config.LLM_MODEL})", inline=True)
        embed.add_field(name="🗺️ 地图 API 状态", value="`已设置 API Key`" if config.GOOGLE_MAPS_API_KEY else "`模拟模式 (未配置 Key)`", inline=True)
        embed.add_field(name="📍 标注策略", value=f"`{config.PINNER_STRATEGY}`", inline=True)

        if config.PINNER_STRATEGY == "sheets":
            sheets_val = f"`{config.GOOGLE_SHEETS_ID[:10]}...`" if config.GOOGLE_SHEETS_ID else "`未配置 GOOGLE_SHEETS_ID`"
            embed.add_field(name="📊 Google Sheet ID", value=sheets_val, inline=False)
        elif config.PINNER_STRATEGY == "kml":
            embed.add_field(name="📄 KML 文件路径", value=f"`{config.KML_OUTPUT_FILE}`", inline=False)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="export_map", description="下载最新生成的 KML 地图标注文件")
    async def export_map(interaction: discord.Interaction):
        kml_path = Path(config.KML_OUTPUT_FILE)
        if not kml_path.exists() or kml_path.stat().st_size == 0:
            await interaction.response.send_message("⚠️ 暂无已生成的 KML 地图文件。", ephemeral=True)
            return

        file = discord.File(str(kml_path), filename=kml_path.name)
        await interaction.response.send_message("📄 最新 KML 地图标注文件（可直接导入 Google My Maps）：", file=file)

    return bot
