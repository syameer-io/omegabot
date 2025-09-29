#!/usr/bin/env python3
"""
Development Setup Script for omegabot
Run this script to test your bot locally before deploying to production.
"""

import os
from dotenv import load_dotenv

def check_environment():
    """Check if development environment is properly configured."""

    # Try to load .env file
    if os.path.exists('.env'):
        load_dotenv()
        print("✅ .env file found and loaded")
    else:
        print("❌ .env file not found!")
        print("📝 Please create .env file based on .env.example")
        return False

    # Check required environment variables
    required_vars = ['DISCORD_TOKEN', 'ANNOUNCEMENT_CHANNEL_ID', 'UPDATE_CHANNEL_ID']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False

    print("✅ All environment variables configured")
    return True

def run_development_bot():
    """Run the bot in development mode."""

    if not check_environment():
        print("\n🛑 Please fix the environment setup first!")
        return

    print("\n🚀 Starting development bot...")
    print("💡 This will run your bot locally with development settings")
    print("⚠️  Make sure your development bot is added to your Discord server")
    print("🔍 Test all commands before deploying to production")
    print("\n📋 Commands to test:")
    print("   - !!nopaypal, !!revolut, !!remitly, !!procinfo")
    print("   - !!key, !!skrill, !!worldremit")
    print("   - /post announce, /post update, /post info")
    print("\n🛑 Press Ctrl+C to stop the development bot\n")

    # Import and run the main bot
    try:
        import bot
        # The bot.py file will automatically use environment variables
        # No need to modify the main file
    except KeyboardInterrupt:
        print("\n👋 Development bot stopped!")
    except Exception as e:
        print(f"\n❌ Error running development bot: {e}")

if __name__ == "__main__":
    print("🔧 omegabot Development Setup")
    print("=" * 40)
    run_development_bot()