"""
Main Entry Point for Xiaohongshu -> Google Maps Discord Bot.
"""

import sys
from config import config
from src.bot.client import create_bot


def main():
    """Start Discord Bot Application."""
    print("=" * 60)
    print("🚀 Xiaohongshu -> Google Maps Discord Bot Starting...")
    print("=" * 60)

    # Configuration validation
    warnings = config.validate()
    if warnings:
        print("\n⚠️ Configuration Warnings:")
        for warn in warnings:
            print(f"  - {warn}")
        print()

    if not config.DISCORD_BOT_TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN is missing! Please configure .env file.")
        print("See README.md or .env.example for instructions.")
        sys.exit(1)

    # Initialize bot
    bot = create_bot()

    try:
        bot.run(config.DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"❌ Failed to run Discord Bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
