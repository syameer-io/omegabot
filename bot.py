# pip install discord.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

# Load .env file for local development (production-safe)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip loading (production environments)

TOKEN = os.getenv('DISCORD_TOKEN')

# Put the target channel IDs here (ints, not strings)
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID', '1389417490651807869'))  # announcement
UPDATE_CHANNEL_ID = int(os.getenv('UPDATE_CHANNEL_ID', '1420408382845751306'))  # update

# --- intents (safe defaults) ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!!", intents=intents)

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


# ---- Button System ----
class AnnouncementView(View):
    """Interactive view with buttons for announcements."""

    def __init__(self, buttons: list = None):
        super().__init__(timeout=None)  # Persistent buttons
        if buttons:
            for button in buttons:
                self.add_item(button)

def create_button(label: str, url: str = None, emoji: str = None, style: discord.ButtonStyle = discord.ButtonStyle.secondary) -> Button:
    """Create a button with the specified parameters."""
    if url:
        # Link button
        button = Button(label=label, url=url, emoji=emoji, style=discord.ButtonStyle.link)
    else:
        # Regular button (for future custom interactions)
        button = Button(label=label, emoji=emoji, style=style, custom_id=f"btn_{label.lower().replace(' ', '_')}")
    return button

def parse_button_params(**kwargs) -> list:
    """Parse button parameters from slash command kwargs and create button list."""
    buttons = []

    for i in range(1, 4):  # Support up to 3 buttons
        label_key = f"button{i}_label"
        url_key = f"button{i}_url"
        emoji_key = f"button{i}_emoji"
        style_key = f"button{i}_style"

        label = kwargs.get(label_key)
        if not label:  # Skip if no label provided
            continue

        url = kwargs.get(url_key)
        emoji = kwargs.get(emoji_key)
        style_param = kwargs.get(style_key, "secondary")

        # Convert style string to ButtonStyle enum
        style_map = {
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
            "link": discord.ButtonStyle.link
        }
        style = style_map.get(style_param.lower(), discord.ButtonStyle.secondary)

        button = create_button(label, url, emoji, style)
        buttons.append(button)

    return buttons


# ---- mention helpers ----
def parse_role_mentions(guild: discord.Guild, role_input: str | None) -> list[discord.Role]:
    """Parse comma-separated role names/IDs and return valid Role objects."""
    if not role_input:
        return []

    roles = []
    role_parts = [part.strip() for part in role_input.split(',')]

    for part in role_parts:
        if not part:
            continue

        role = None
        # Try to find by ID first (if it's all digits)
        if part.isdigit():
            role = guild.get_role(int(part))

        # If not found by ID, try by name
        if not role:
            role = discord.utils.get(guild.roles, name=part)

        if role:
            roles.append(role)

    return roles

def build_mention_content(mention_everyone: bool = False, mention_roles: list[discord.Role] = None) -> str:
    """Build mention string for the message."""
    mentions = []

    if mention_everyone:
        mentions.append("@everyone")

    if mention_roles:
        for role in mention_roles:
            mentions.append(role.mention)

    return " ".join(mentions)

def can_mention_everyone(interaction: discord.Interaction) -> bool:
    """Check if user can use @everyone mentions (Admin only)."""
    return interaction.user.guild_permissions.administrator or any(role.name in {"Owner", "Admin"} for role in interaction.user.roles)

# ---- helpers ----
async def send_embed(channel: discord.TextChannel, *, title: str, body: str, footer: str | None = None, buttons: list = None, mention_everyone: bool = False, mention_roles: list[discord.Role] = None):
    """Build a clean announcement-style embed with optional buttons and mentions."""
    embed = discord.Embed(
        title=title.strip()[:256],
        description=body.strip()[:4096],
        color=discord.Color.blurple()
    )
    if footer:
        embed.set_footer(text=footer[:2048])
    # Optional: add a small "app" tag vibe
    embed.set_author(name="Omegaberg | Official Shop")  # change to your brand

    # Create view with buttons if provided
    view = None
    if buttons:
        view = AnnouncementView(buttons)

    # Build mention content
    mention_content = build_mention_content(mention_everyone, mention_roles)

    # Set up allowed mentions to control ping behavior
    allowed_mentions = discord.AllowedMentions(
        everyone=mention_everyone,
        roles=bool(mention_roles)
    )

    # Send mention content with embed
    if mention_content:
        return await channel.send(content=mention_content, embed=embed, view=view, allowed_mentions=allowed_mentions)
    else:
        return await channel.send(embed=embed, view=view)

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
    @app_commands.describe(
        title="Headline of the post",
        body="Main content (supports Markdown)",
        footer="Optional small footer",
        mention_everyone="Mention @everyone (Admin only)",
        mention_roles="Comma-separated role names/IDs to mention",
        button1_label="Label for first button",
        button1_url="URL for first button",
        button1_emoji="Emoji for first button (optional)",
        button1_style="Style for first button (primary/secondary/success/danger)",
        button2_label="Label for second button",
        button2_url="URL for second button",
        button2_emoji="Emoji for second button (optional)",
        button2_style="Style for second button (primary/secondary/success/danger)",
        button3_label="Label for third button",
        button3_url="URL for third button",
        button3_emoji="Emoji for third button (optional)",
        button3_style="Style for third button (primary/secondary/success/danger)"
    )
    async def announce(self, interaction: discord.Interaction,
                      title: str,
                      body: str,
                      footer: str | None = None,
                      mention_everyone: bool = False,
                      mention_roles: str | None = None,
                      button1_label: str | None = None,
                      button1_url: str | None = None,
                      button1_emoji: str | None = None,
                      button1_style: str = "secondary",
                      button2_label: str | None = None,
                      button2_url: str | None = None,
                      button2_emoji: str | None = None,
                      button2_style: str = "secondary",
                      button3_label: str | None = None,
                      button3_url: str | None = None,
                      button3_emoji: str | None = None,
                      button3_style: str = "secondary"):
        if not staff_only(interaction):
            return await interaction.response.send_message("You don't have permission to post here.", ephemeral=True)

        # Check @everyone permission
        if mention_everyone and not can_mention_everyone(interaction):
            return await interaction.response.send_message("You don't have permission to use @everyone mentions.", ephemeral=True)

        channel = interaction.client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Announcement channel not found. Check the ID.", ephemeral=True)

        # 🔽 convert "\n" etc. to real newlines
        title  = _multiline(title)[:256]
        body   = _multiline(body)[:4096]
        footer = _multiline(footer)[:2048] if footer else None

        # Parse role mentions
        roles_to_mention = parse_role_mentions(interaction.guild, mention_roles)

        # Parse button parameters
        button_kwargs = {
            "button1_label": button1_label, "button1_url": button1_url, "button1_emoji": button1_emoji, "button1_style": button1_style,
            "button2_label": button2_label, "button2_url": button2_url, "button2_emoji": button2_emoji, "button2_style": button2_style,
            "button3_label": button3_label, "button3_url": button3_url, "button3_emoji": button3_emoji, "button3_style": button3_style
        }
        buttons = parse_button_params(**button_kwargs)

        await interaction.response.defer(ephemeral=True)
        msg = await send_embed(channel, title=title, body=body, footer=footer, buttons=buttons, mention_everyone=mention_everyone, mention_roles=roles_to_mention)

        # Build mention summary for confirmation
        mention_summary = []
        if mention_everyone:
            mention_summary.append("@everyone")
        if roles_to_mention:
            mention_summary.extend([role.name for role in roles_to_mention])

        mention_text = f" (mentioned: {', '.join(mention_summary)})" if mention_summary else ""
        await interaction.followup.send(f"Posted to {channel.mention}: {msg.jump_url}{mention_text}", ephemeral=True)

    @app_commands.command(name="update", description="Post to the update channel")
    @app_commands.describe(
        title="Headline of the update",
        body="Main content (supports Markdown)",
        footer="Optional small footer",
        mention_everyone="Mention @everyone (Admin only)",
        mention_roles="Comma-separated role names/IDs to mention",
        button1_label="Label for first button",
        button1_url="URL for first button",
        button1_emoji="Emoji for first button (optional)",
        button1_style="Style for first button (primary/secondary/success/danger)",
        button2_label="Label for second button",
        button2_url="URL for second button",
        button2_emoji="Emoji for second button (optional)",
        button2_style="Style for second button (primary/secondary/success/danger)",
        button3_label="Label for third button",
        button3_url="URL for third button",
        button3_emoji="Emoji for third button (optional)",
        button3_style="Style for third button (primary/secondary/success/danger)"
    )
    async def update(self, interaction: discord.Interaction,
                    title: str,
                    body: str,
                    footer: str | None = None,
                    mention_everyone: bool = False,
                    mention_roles: str | None = None,
                    button1_label: str | None = None,
                    button1_url: str | None = None,
                    button1_emoji: str | None = None,
                    button1_style: str = "secondary",
                    button2_label: str | None = None,
                    button2_url: str | None = None,
                    button2_emoji: str | None = None,
                    button2_style: str = "secondary",
                    button3_label: str | None = None,
                    button3_url: str | None = None,
                    button3_emoji: str | None = None,
                    button3_style: str = "secondary"):
        if not staff_only(interaction):
            return await interaction.response.send_message("You don't have permission to post here.", ephemeral=True)

        # Check @everyone permission
        if mention_everyone and not can_mention_everyone(interaction):
            return await interaction.response.send_message("You don't have permission to use @everyone mentions.", ephemeral=True)

        channel = interaction.client.get_channel(UPDATE_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Update channel not found. Check the ID.", ephemeral=True)

        # 🔽 convert "\n" etc. to real newlines
        title  = _multiline(title)[:256]
        body   = _multiline(body)[:4096]
        footer = _multiline(footer)[:2048] if footer else None

        # Parse role mentions
        roles_to_mention = parse_role_mentions(interaction.guild, mention_roles)

        # Parse button parameters
        button_kwargs = {
            "button1_label": button1_label, "button1_url": button1_url, "button1_emoji": button1_emoji, "button1_style": button1_style,
            "button2_label": button2_label, "button2_url": button2_url, "button2_emoji": button2_emoji, "button2_style": button2_style,
            "button3_label": button3_label, "button3_url": button3_url, "button3_emoji": button3_emoji, "button3_style": button3_style
        }
        buttons = parse_button_params(**button_kwargs)

        await interaction.response.defer(ephemeral=True)
        msg = await send_embed(channel, title=title, body=body, footer=footer, buttons=buttons, mention_everyone=mention_everyone, mention_roles=roles_to_mention)

        # Build mention summary for confirmation
        mention_summary = []
        if mention_everyone:
            mention_summary.append("@everyone")
        if roles_to_mention:
            mention_summary.extend([role.name for role in roles_to_mention])

        mention_text = f" (mentioned: {', '.join(mention_summary)})" if mention_summary else ""
        await interaction.followup.send(f"Posted to {channel.mention}: {msg.jump_url}{mention_text}", ephemeral=True)

    @app_commands.command(name="info", description="Post Ultrathink information to current channel")
    @app_commands.describe(
        key="The access key to display"
    )
    async def info(self, interaction: discord.Interaction, key: str):
        if not staff_only(interaction):
            return await interaction.response.send_message("You don't have permission to post here.", ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("This command can only be used in text channels.", ephemeral=True)

        # Fixed content
        title = "Delta Force Mobile - Setup Guide"
        body = f"**Access Key:** `{key}`\n\n**Setup Instructions:**\n1. Install VPhone OS using the link provided (thru google play store official).\n2. Launch and follow the step to bypass process killer to ensure vphone os works smoothly.\n3. Create VM, choose Android 12, Choose 64 bit and check Optimized for Games (Make sure you have the VIP version which will cost extra. No modded apk for VIP unlocked yet as of now because vphone os is new.)\n4. Install delta force officially from playstore (if you havent), install the injector using MT Manager (VERY IMPORTANT! Because mt manager bypasses extra things when installed)\n5. Make sure delta force is atleast launched once in your phone and installed all the necessary game files.\n6. Import delta force and the injector into VPhone OS VM that you created.\n7. Launch delta force again and install the necessary game files in vphone os. Fully close it after.\n8. Launch the injector and input your key.\n9. Go to hacks tab below, choose either global or garena, and choose syscall.\n10. Click start and ensure the menu appeared on top left.\n11. Go back to protection tab and choose either global or garena and the game will launch for you.\n12. Get into a match until you are spawned in, click on the menu and click on Initialize (make sure to select your correct gamemode eg. warfare)"

        # Create download button
        download_button = create_button("Download Loader", "https://www.mediafire.com/file/4d442xdxev8kuib/DELTA_FORCE_VVIP.rar/file", None, discord.ButtonStyle.primary)
        buttons = [download_button]

        await interaction.response.defer(ephemeral=True)
        msg = await send_embed(channel, title=title, body=body, buttons=buttons)

        await interaction.followup.send(f"Posted Ultrathink info to {channel.mention}: {msg.jump_url}", ephemeral=True)

bot.tree.add_command(AnnounceGroup(name="post", description="Post announcements and updates"))

# ---- Traditional Commands ----
@bot.command()
async def nopaypal(ctx):
    """Display alternative payment options information."""

    embed = discord.Embed(
        title="🌐 Payment Update Notice 🌐",
        description="Hello! Thank you for your interest in our products and services.",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="⚠️ Important Notice",
        value="At this time, we do not accept PayPal for payments. However, we have five secure alternatives that support both debit and credit card transactions:",
        inline=False
    )

    alternatives = (
        "✅ **Revolut**\n"
        "✅ **WorldRemit**\n"
        "✅ **Remitly**\n"
        "✅ **Skrill**\n"
        "✅ **Skrill Gift Card via G2A**"
    )

    embed.add_field(
        name="💳 Available Payment Methods",
        value=alternatives,
        inline=False
    )

    embed.add_field(
        name="💡 About These Platforms",
        value="These platforms are reliable and widely used as excellent replacements for PayPal.",
        inline=False
    )

    embed.add_field(
        name="💬 Next Steps",
        value="Kindly let us know which payment method you prefer, and we'll provide you with the necessary details to proceed.",
        inline=False
    )

    embed.set_footer(text="Thank you for your understanding and continued trust in our business!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def revolut(ctx):
    """Display Revolut payment instructions."""

    embed = discord.Embed(
        title="🔵 Revolut - How to Purchase",
        description="Follow these steps to complete your payment via Revolut:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📋 Step-by-Step Instructions",
        value=(
            "1️⃣ Go to one of the processors below (Processor 1 or Processor 2)\n"
            "2️⃣ Send the amount + service fee (+2.5 EUR for day key, +5 EUR for week/month key)\n"
            "3️⃣ Send screenshot of receipt in ticket\n"
            "4️⃣ Ping @milkermyers and @odysseas\n"
            "5️⃣ Wait for processor to confirm payment"
        ),
        inline=False
    )

    embed.add_field(
        name="💳 Processor Links",
        value=(
            "**Processor 1:** https://revolut.me/adolfmyers\n"
            "**Processor 2:** https://revolut.me/odysseas1999"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Note",
        value="We do not accept payment without service fee included. Please pay the correct amount so that the flow will be smooth.",
        inline=False
    )

    embed.set_footer(text="Please ensure you include the service fee for smooth processing!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def remitly(ctx):
    """Display Remitly payment instructions."""

    embed = discord.Embed(
        title="📧 Remitly Instructions",
        description="Follow these steps to set up your Remitly payment:",
        color=discord.Color.green()
    )

    embed.add_field(
        name="📋 Step-by-Step Instructions",
        value=(
            "1️⃣ Create account here: https://www.remitly.com/au/en/philippines\n"
            "2️⃣ After creating account, it will ask for receiver details\n"
            "3️⃣ For total amount, mention @omegaberg to get correct amount (follow Google conversion)\n"
            "4️⃣ Choose Delivery Method → Mobile Money → GCASH\n"
            "5️⃣ Choose your preferred payment method\n"
            "6️⃣ Screenshot the next page in your ticket"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Important Note",
        value="We will provide the Handler's information afterwards in your ticket.",
        inline=False
    )

    embed.set_footer(text="Make sure to screenshot the confirmation page for your ticket!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def procinfo(ctx):
    """Display processor information for payments."""

    embed = discord.Embed(
        title="📋 Processor Information",
        description="✅ **REMITLY AND WORLDREMIT PAYMENT INFO** ✅",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="👤 Receiver Details",
        value=(
            "**First Name:** J Patrick Alben\n"
            "**Last Name:** Ofrecio\n"
            "**Mobile #:** 09215633047 or 639215633047 (63 = PH country code)\n"
            "**Country:** Philippines"
        ),
        inline=False
    )

    embed.add_field(
        name="💳 Accepted Payment Methods",
        value="GCash, Mobile Wallet, Maya Wallet",
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Warning",
        value="👉 Please double-check the details before sending your payment.",
        inline=False
    )

    embed.add_field(
        name="📸 Final Note",
        value="Once sent, kindly provide a screenshot or transaction reference for faster confirmation. Thank you!",
        inline=False
    )

    embed.set_footer(text="Double-check all details before proceeding with your payment!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def key(ctx):
    """Display key access and loader download instructions."""

    embed = discord.Embed(
        title="🔑 Access Your Key & Download Loader",
        description="Follow these instructions to access your key and download the necessary files:",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="🔐 Key Access",
        value=(
            "You will see your key here\n"
            "**Key Link:** https://omegaberg.com/clients/purchases/"
        ),
        inline=False
    )

    embed.add_field(
        name="📥 Download Loader",
        value="**Loader Link:** https://omegaberg.com/files/",
        inline=False
    )

    embed.add_field(
        name="📋 Instructions",
        value=(
            "1️⃣ Find the product that you purchased on the categories (Right side)\n"
            "2️⃣ Expand it and find the product"
        ),
        inline=False
    )

    embed.set_footer(text="Keep your key secure and only download from official links!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def skrill(ctx):
    """Display Skrill payment instructions."""

    embed = discord.Embed(
        title="💰 Skrill Instructions",
        description="For Skrill payments, it is same like paypal but it is more easier!",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="📋 Step-by-Step Instructions",
        value=(
            "1️⃣ Login to Skrill\n"
            "2️⃣ Choose send money (skrill to skrill)\n"
            "3️⃣ **Account email:** alex.killerproT@gmail.com\n"
            "4️⃣ When sending payments, use the skrill calculator for money conversion\n"
            "5️⃣ Click send\n"
            "6️⃣ **DO NOT ADD A MESSAGE OR NOTE WHEN SENDING PAYMENT**\n"
            "7️⃣ Send us the receipt and name on skrill"
        ),
        inline=False
    )

    embed.add_field(
        name="💶 Currency Information",
        value="**NOTE:** We follow EURO currency and please add 5 euros fees on top of the STORE price.",
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Warning",
        value="Do not include any messages or notes with your payment!",
        inline=False
    )

    embed.set_footer(text="Remember: No messages or notes - send receipt and name only!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def worldremit(ctx):
    """Display World Remit payment instructions."""

    embed = discord.Embed(
        title="🌍 World Remit Instructions",
        description="Here's how you can pay using World Remit",
        color=discord.Color.teal()
    )

    embed.add_field(
        name="📋 Setup Instructions",
        value=(
            "1️⃣ Go to this link: https://www.worldremit.com/en?amountfrom=100.00&selectfrom=us&currencyfrom=usd&selectto=ph&currencyto=php&transfer=mob\n"
            "2️⃣ Change \"You Send\" Country to your country\n"
            "3️⃣ Type the amount that you will be sending (NOTE: We will follow google conversion for this. ASK THE SUPPORT)\n"
            "4️⃣ Click Receive Method and change it to Mobile Money\n"
            "5️⃣ Click Continue\n"
            "6️⃣ Select Partner and change it to Gcash/Paymaya (Please verify this in your ticket first)\n"
            "7️⃣ Click Continue"
        ),
        inline=False
    )

    embed.add_field(
        name="📝 Registration Details",
        value=(
            "**Sending from:** your country\n"
            "**State:** your state\n"
            "**Sending to:** Philippines\n"
            "**Add your email address**\n"
            "**Create your password**"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Final Note",
        value="Once you are registered, it will ask you for a credential of the payment handler. Please screenshot it and send it to your ticket thank you.",
        inline=False
    )

    embed.set_footer(text="Always verify details in your ticket before proceeding!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def status(ctx):
    """Display current bot and service status information."""

    embed = discord.Embed(
        title="📊 Omegaberg Bot Status",
        description="Current status of our Discord bot and services",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🤖 Bot Status",
        value="✅ **Online and Operational**\n🔄 All commands functioning normally",
        inline=False
    )

    embed.add_field(
        name="💳 Payment Services",
        value="✅ **All payment methods available**\n• Revolut, Remitly, WorldRemit\n• Skrill and processor payments active",
        inline=False
    )

    embed.add_field(
        name="🛠️ Available Commands",
        value="**Information Commands:**\n`!!nopaypal`, `!!revolut`, `!!remitly`, `!!procinfo`\n`!!key`, `!!skrill`, `!!worldremit`, `!!createorder`, `!!status`",
        inline=False
    )

    embed.add_field(
        name="📞 Support",
        value="For assistance, create a support ticket or contact staff members.",
        inline=False
    )

    embed.set_footer(text="Status updated automatically • All systems operational")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.command()
async def createorder(ctx):
    """Display instructions for creating an order on Omegaberg."""

    embed = discord.Embed(
        title="📦 How to Create an Order",
        description="Welcome! Follow these simple steps to create your order on Omegaberg:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📝 Step-by-Step Instructions",
        value=(
            "1️⃣ Create an account on https://omegaberg.com\n"
            "2️⃣ Go to the store and click on the product you want to purchase\n"
            "3️⃣ Click on your desired product subscription, then add to cart\n"
            "4️⃣ Click 'Review and Checkout'\n"
            "   • Address is not required\n"
            "   • No need to pay at this step\n"
            "5️⃣ Choose **'Manual'** under payment method\n"
            "6️⃣ Click **'Place order and pay'**\n"
            "7️⃣ Send your order number to support (e.g., Order #23455)"
        ),
        inline=False
    )

    embed.set_footer(text="Need help? Create a support ticket or contact staff members!")
    embed.set_author(name="Omegaberg | Official Shop")

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    # Sync slash commands to all guilds the bot is in
    try:
        synced = await bot.tree.sync()
        print(f"[SUCCESS] Logged in as {bot.user} - {len(synced)} slash commands synced")
    except Exception as e:
        print(f"[ERROR] Failed to sync commands: {e}")

bot.run(TOKEN)
