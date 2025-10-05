#!/usr/bin/env python3
"""
Development Setup Script for omegabot
Run this script to test your bot locally before deploying to production.
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if development environment is properly configured."""

    # Try to load .env file
    if os.path.exists('.env'):
        load_dotenv()
        print("[OK] .env file found and loaded")
    else:
        print("[ERROR] .env file not found!")
        print("[INFO] Please create .env file based on .env.example")
        return False

    # Check required environment variables
    required_vars = ['DISCORD_TOKEN', 'ANNOUNCEMENT_CHANNEL_ID', 'UPDATE_CHANNEL_ID']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here":
            missing_vars.append(var)

    if missing_vars:
        print(f"[ERROR] Missing or unconfigured environment variables: {', '.join(missing_vars)}")
        print("[INFO] Please edit the .env file with your actual bot token and channel IDs")
        return False

    print("[OK] All environment variables configured")
    return True

def run_development_bot():
    """Run the bot in development mode."""

    print("omegabot Development Setup")
    print("=" * 40)

    if not check_environment():
        print("\n[STOP] Please fix the environment setup first!")
        print("\n[NEXT STEPS]")
        print("1. Edit the .env file with your development bot token")
        print("2. Replace 'your_development_bot_token_here' with actual token")
        print("3. Ensure your development bot is added to Discord server")
        print("4. Run this script again")
        return

    print("\n[STARTING] Development bot...")
    print("[INFO] This will run your bot locally with development settings")
    print("[WARNING] Make sure your development bot is added to your Discord server")
    print("[INFO] Test all commands before deploying to production")
    print("\n[COMMANDS TO TEST]")
    print("   - !!nopaypal, !!revolut, !!remitly, !!procinfo")
    print("   - !!key, !!skrill, !!worldremit, !!status")
    print("   - /post announce, /post update, /post info")
    print("\n[STOP] Press Ctrl+C to stop the development bot\n")

    # Import and run the main bot
    try:
        import bot
        # The bot.py file will automatically use environment variables
        # No need to modify the main file
    except KeyboardInterrupt:
        print("\n[STOPPED] Development bot stopped!")
    except Exception as e:
        print(f"\n[ERROR] Error running development bot: {e}")
        print("[DEBUG] Make sure discord.py is installed: pip install discord.py")

if __name__ == "__main__":
    run_development_bot()