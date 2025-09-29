# pip install discord.py
import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv('DISCORD_TOKEN')

# Put the target channel IDs here (ints, not strings)
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID', '1420408380404793554'))  # 📢-announcement
UPDATE_CHANNEL_ID = int(os.getenv('UPDATE_CHANNEL_ID', '1420408382845751306'))  # 🛠️-update

# --- intents (safe defaults) ---
intents = discord.Intents.default()
intents.message_content = False
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- helpers for line breaks ---
def _multiline(s: str | None) -> str | None:
    if s is None:
        return None
    # Turn typed backslash escapes into real newlines/tabs
    return (
        s.replace("\\r\\n", "\n")
         .replace("\\n", "\n")
         .replace("\\r", "\n")
         .replace("\\t", "\t")
         .strip()
    )


# ---- helpers ----
async def send_embed(channel: discord.TextChannel, *, title: str, body: str, footer: str | None = None):
    """Build a clean announcement-style embed like your screenshot."""
    embed = discord.Embed(
        title=title.strip()[:256],
        description=body.strip()[:4096],
        color=discord.Color.blurple()
    )
    if footer:
        embed.set_footer(text=footer[:2048])
    # Optional: add a small “app” tag vibe
    embed.set_author(name="Omegaberg | Official Shop")  # change to your brand
    return await channel.send(embed=embed)

def staff_only(interaction: discord.Interaction) -> bool:
    """Allow Owner/Admin (and optionally Support) to post."""
    if interaction.user.guild_permissions.administrator:
        return True
    # Add role names that are allowed to post:
    allowed_role_names = {"Owner", "Admin", "Support"}
    user_role_names = {r.name for r in interaction.user.roles}
    return len(allowed_role_names & user_role_names) > 0

# ---- slash command group (optional) ----
@app_commands.default_permissions(administrator=True)
class AnnounceGroup(app_commands.Group):
    """Post announcements/updates as embeds."""

    @app_commands.command(name="announce", description="Post to the announcement channel")
    @app_commands.describe(title="Headline of the post", body="Main content (supports Markdown)", footer="Optional small footer")
    async def announce(self, interaction: discord.Interaction, title: str, body: str, footer: str | None = None):
        if not staff_only(interaction):
            return await interaction.response.send_message("You don’t have permission to post here.", ephemeral=True)

        channel = interaction.client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Announcement channel not found. Check the ID.", ephemeral=True)

        # 🔽 convert "\n" etc. to real newlines
        title  = _multiline(title)[:256]
        body   = _multiline(body)[:4096]
        footer = _multiline(footer)[:2048] if footer else None

        await interaction.response.defer(ephemeral=True)
        msg = await send_embed(channel, title=title, body=body, footer=footer)
        await interaction.followup.send(f"Posted to {channel.mention}: {msg.jump_url}", ephemeral=True)

    @app_commands.command(name="update", description="Post to the update channel")
    @app_commands.describe(title="Headline of the update", body="Main content (supports Markdown)", footer="Optional small footer")
    async def update(self, interaction: discord.Interaction, title: str, body: str, footer: str | None = None):
        if not staff_only(interaction):
            return await interaction.response.send_message("You don’t have permission to post here.", ephemeral=True)

        channel = interaction.client.get_channel(UPDATE_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Update channel not found. Check the ID.", ephemeral=True)

        # 🔽 convert "\n" etc. to real newlines
        title  = _multiline(title)[:256]
        body   = _multiline(body)[:4096]
        footer = _multiline(footer)[:2048] if footer else None

        await interaction.response.defer(ephemeral=True)
        msg = await send_embed(channel, title=title, body=body, footer=footer)
        await interaction.followup.send(f"Posted to {channel.mention}: {msg.jump_url}", ephemeral=True)

bot.tree.add_command(AnnounceGroup(name="post", description="Post announcements and updates"))

@bot.event
async def on_ready():
    # Sync slash commands to all guilds the bot is in
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} — slash commands synced")

bot.run(TOKEN)
