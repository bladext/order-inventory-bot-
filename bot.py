import discord
from discord.ext import commands
from discord import app_commands
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

INVENTORY_FILE = "inventory.json"
MESSAGE_FILE = "message.json"

CATEGORIES = ["weapons", "armor", "ammo", "drugs", "misc"]

# ---------------- FILE HELPERS ----------------

def load_data():
    if not os.path.exists(INVENTORY_FILE):
        return {c: {} for c in CATEGORIES}, {}
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    return data.get("inventory", {}), data.get("loans", {})

def save_data(inventory, loans):
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

# ---------------- EMBED UPDATE ----------------

async def update_inventory_embed(guild):
    inventory, loans = load_data()
    msg_data = load_message()
    if not msg_data:
        return

    channel = guild.get_channel(msg_data["channel_id"])
    message = await channel.fetch_message(msg_data["message_id"])

    embed = discord.Embed(
        title="📦 Ørder Storage",
        color=discord.Color.dark_red()
    )

    for cat in CATEGORIES:
        items = inventory.get(cat, {})
        value = "\n".join(f"• {k}: {v}" for k, v in items.items()) or "—"
        embed.add_field(name=cat.capitalize(), value=value, inline=False)

    loan_lines = []
    for uid, items in loans.items():
        for item, amt in items.items():
            loan_lines.append(f"<@{uid}> owes {amt}x {item}")
    embed.add_field(
        name="📄 Loans",
        value="\n".join(loan_lines) or "—",
        inline=False
    )

    await message.edit(embed=embed)

# ---------------- BOT EVENTS ----------------

@bot.event
async def setup_hook():
    GUILD_ID = 192108930388721664  # your server ID
    guild = discord.Object(id=GUILD_ID)

    # Clear global commands (prevents cache conflicts)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    # Sync guild-only commands (instant)
    await bot.tree.sync(guild=guild)

    print("✅ Guild slash commands synced")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for g in bot.guilds:
        print("Connected to:", g.name, g.id)

# ---------------- SLASH COMMANDS ----------------

@bot.tree.command(name="ping", description="Test command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

@bot.tree.command(name="setup_inventory", description="Create the persistent inventory message")
async def setup_inventory(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 Ørder Storage",
        description="Inventory initialized",
        color=discord.Color.dark_red()
    )
    msg = await interaction.channel.send(embed=embed)
    save_message({"channel_id": interaction.channel.id, "message_id": msg.id})
    await interaction.response.send_message("✅ Inventory setup complete.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="deposit", description="Deposit items into storage")
async def deposit(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    category = category.lower()
    if category not in CATEGORIES:
        await interaction.response.send_message(
            f"❌ Invalid category. Use: {', '.join(CATEGORIES)}",
            ephemeral=True
        )
        return

    inventory, loans = load_data()
    inventory.setdefault(category, {})
    inventory[category][item] = inventory[category].get(item, 0) + amount
    save_data(inventory, loans)

    await interaction.response.send_message("✅ Deposited.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="withdraw", description="Withdraw items from storage")
async def withdraw(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    category = category.lower()
    inventory, loans = load_data()

    if inventory.get(category, {}).get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock.", ephemeral=True)
        return

    inventory[category][item] -= amount
    if inventory[category][item] <= 0:
        del inventory[category][item]

    save_data(inventory, loans)
    await interaction.response.send_message("📤 Withdrawn.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="loan", description="Loan items to a member")
async def loan(
    interaction: discord.Interaction,
    member: discord.Member,
    item: str,
    amount: int
):
    inventory, loans = load_data()
    loans.setdefault(str(member.id), {})
    loans[str(member.id)][item] = loans[str(member.id)].get(item, 0) + amount
    save_data(inventory, loans)

    await interaction.response.send_message("📄 Loan recorded.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="pay", description="Pay back loaned items")
async def pay(
    interaction: discord.Interaction,
    item: str,
    amount: int
):
    inventory, loans = load_data()
    uid = str(interaction.user.id)

    if uid not in loans or loans[uid].get(item, 0) < amount:
        await interaction.response.send_message("❌ No matching loan found.", ephemeral=True)
        return

    loans[uid][item] -= amount
    if loans[uid][item] <= 0:
        del loans[uid][item]
    if not loans[uid]:
        del loans[uid]

    save_data(inventory, loans)
    await interaction.response.send_message("✅ Loan paid.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

# ---------------- RUN ----------------

bot.run(TOKEN)
