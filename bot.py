import discord
from discord import app_commands
from discord.ext import commands
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 192108930388721664

INTENTS = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=INTENTS)

INVENTORY_FILE = "inventory.json"
MESSAGE_FILE = "message.json"

CATEGORIES = ["weapons", "armor", "ammo", "drugs", "misc"]

# ------------------------
# Utility Functions
# ------------------------

def load_inventory():
    if not os.path.exists(INVENTORY_FILE):
        return {c: {} for c in CATEGORIES}, {}
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    return data.get("inventory", {}), data.get("loans", {})

def save_inventory(inventory, loans):
    with open(INVENTORY_FILE, "w") as f:
        json.dump({"inventory": inventory, "loans": loans}, f, indent=2)

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        return None
    with open(MESSAGE_FILE, "r") as f:
        return json.load(f)

def save_message(data):
    with open(MESSAGE_FILE, "w") as f:
        json.dump(data, f)

async def update_embed(guild):
    inventory, loans = load_inventory()
    msg_data = load_message()
    if not msg_data:
        return

    channel = guild.get_channel(msg_data["channel_id"])
    if not channel:
        return

    message = await channel.fetch_message(msg_data["message_id"])

    embed = discord.Embed(
        title="📦 Ørder Storage",
        color=discord.Color.dark_red()
    )

    for category in CATEGORIES:
        items = inventory.get(category, {})
        text = "\n".join(f"• {k}: {v}" for k, v in items.items()) or "—"
        embed.add_field(name=category.capitalize(), value=text, inline=False)

    loan_text = []
    for user, items in loans.items():
        for item, amt in items.items():
            loan_text.append(f"<@{user}> owes {amt}x {item}")
    embed.add_field(
        name="📄 Loans",
        value="\n".join(loan_text) or "—",
        inline=False
    )

    await message.edit(embed=embed)

# ------------------------
# Bot Setup (CRITICAL FIX)
# ------------------------

@bot.event
async def setup_hook():
    guild = discord.Object(id=GUILD_ID)

    # 🔥 DELETE ALL GLOBAL COMMANDS (fixes your crash)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    # ✅ REGISTER CLEAN GUILD COMMANDS ONLY
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    print("🔥 Global commands purged, guild commands synced")

# ------------------------
# Events
# ------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ------------------------
# Slash Commands
# ------------------------

@bot.tree.command(name="setup_inventory")
async def setup_inventory(interaction: discord.Interaction):
    inventory, loans = load_inventory()

    embed = discord.Embed(
        title="📦 Ørder Storage",
        description="Inventory tracking is now active.",
        color=discord.Color.dark_red()
    )

    msg = await interaction.channel.send(embed=embed)
    save_message({
        "channel_id": interaction.channel.id,
        "message_id": msg.id
    })

    await interaction.response.send_message("✅ Storage setup complete.", ephemeral=True)
    await update_embed(interaction.guild)

@bot.tree.command(name="deposit")
async def deposit(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    category = category.lower()

    if category not in CATEGORIES:
        await interaction.response.send_message("❌ Invalid category.", ephemeral=True)
        return

    inventory, loans = load_inventory()
    inventory.setdefault(category, {})
    inventory[category][item] = inventory[category].get(item, 0) + amount
    save_inventory(inventory, loans)

    await interaction.response.send_message(f"✅ Deposited {amount}x {item}.", ephemeral=True)
    await update_embed(interaction.guild)

@bot.tree.command(name="withdraw")
async def withdraw(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    category = category.lower()
    inventory, loans = load_inventory()

    if inventory.get(category, {}).get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock.", ephemeral=True)
        return

    inventory[category][item] -= amount
    if inventory[category][item] <= 0:
        del inventory[category][item]

    save_inventory(inventory, loans)
    await interaction.response.send_message(f"📤 Withdrew {amount}x {item}.", ephemeral=True)
    await update_embed(interaction.guild)

@bot.tree.command(name="loan")
async def loan(
    interaction: discord.Interaction,
    member: discord.Member,
    item: str,
    amount: int
):
    inventory, loans = load_inventory()

    loans.setdefault(str(member.id), {})
    loans[str(member.id)][item] = loans[str(member.id)].get(item, 0) + amount

    save_inventory(inventory, loans)
    await interaction.response.send_message(f"📄 Loaned {amount}x {item} to {member.mention}.", ephemeral=True)
    await update_embed(interaction.guild)

@bot.tree.command(name="pay")
async def pay(
    interaction: discord.Interaction,
    item: str,
    amount: int
):
    inventory, loans = load_inventory()
    uid = str(interaction.user.id)

    if uid not in loans or loans[uid].get(item, 0) < amount:
        await interaction.response.send_message("❌ No such loan.", ephemeral=True)
        return

    loans[uid][item] -= amount
    if loans[uid][item] <= 0:
        del loans[uid][item]
    if not loans[uid]:
        del loans[uid]

    save_inventory(inventory, loans)
    await interaction.response.send_message(f"✅ Paid back {amount}x {item}.", ephemeral=True)
    await update_embed(interaction.guild)

# ------------------------
# Run Bot
# ------------------------

bot.run(TOKEN)
