import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 192108930388721664  # YOUR SERVER ID

INVENTORY_FILE = "inventory.json"
MESSAGE_FILE = "message.json"

CATEGORIES = ["weapons", "armor", "ammo", "drugs", "misc"]

# ================= BOT SETUP =================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FILE HELPERS =================

def load_data():
    if not os.path.exists(INVENTORY_FILE):
        return {c: {} for c in CATEGORIES}, {}
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    return data.get("inventory", {}), data.get("loans", {})

def save_data(inventory, loans):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(
            {"inventory": inventory, "loans": loans},
            f,
            indent=2
        )

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        return None
    with open(MESSAGE_FILE, "r") as f:
        return json.load(f)

def save_message(data):
    with open(MESSAGE_FILE, "w") as f:
        json.dump(data, f)

# ================= EMBED UPDATE =================

async def update_inventory_embed(guild: discord.Guild):
    msg_data = load_message()
    if not msg_data:
        return

    inventory, loans = load_data()

    channel = guild.get_channel(msg_data["channel_id"])
    if not channel:
        return

    message = await channel.fetch_message(msg_data["message_id"])

    embed = discord.Embed(
        title="📦 Ørder Storage",
        color=discord.Color.dark_red()
    )

    for cat in CATEGORIES:
        items = inventory.get(cat, {})
        value = "\n".join(f"• {k}: {v}" for k, v in items.items()) or "—"
        embed.add_field(
            name=cat.capitalize(),
            value=value,
            inline=False
        )

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

# ================= EVENTS =================

@bot.event
async def setup_hook():
    guild = discord.Object(id=GUILD_ID)

    # 🚨 DELETE ALL GLOBAL COMMANDS
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    # ✅ REGISTER GUILD COMMANDS ONLY
    await bot.tree.sync(guild=guild)

    print("🔥 GUILD SLASH COMMANDS SYNCED 🔥")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for g in bot.guilds:
        print("Connected to:", g.name, g.id)

# ================= COMMANDS =================

@bot.tree.command(name="ping", description="Test command", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

@bot.tree.command(name="setup_inventory", description="Create inventory embed", guild=discord.Object(id=GUILD_ID))
async def setup_inventory(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 Ørder Storage",
        description="Inventory initialized",
        color=discord.Color.dark_red()
    )
    msg = await interaction.channel.send(embed=embed)
    save_message({
        "channel_id": interaction.channel.id,
        "message_id": msg.id
    })

    await interaction.response.send_message(
        "✅ Inventory setup complete.",
        ephemeral=True
    )
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="deposit", description="Deposit items", guild=discord.Object(id=GUILD_ID))
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

@bot.tree.command(name="withdraw", description="Withdraw items", guild=discord.Object(id=GUILD_ID))
async def withdraw(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    category = category.lower()
    inventory, loans = load_data()

    if inventory.get(category, {}).get(item, 0) < amount:
        await interaction.response.send_message(
            "❌ Not enough stock.",
            ephemeral=True
        )
        return

    inventory[category][item] -= amount
    if inventory[category][item] <= 0:
        del inventory[category][item]

    save_data(inventory, loans)

    await interaction.response.send_message("📤 Withdrawn.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="loan", description="Loan items", guild=discord.Object(id=GUILD_ID))
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

@bot.tree.command(name="pay", description="Pay back loans", guild=discord.Object(id=GUILD_ID))
async def pay(
    interaction: discord.Interaction,
    item: str,
    amount: int
):
    inventory, loans = load_data()
    uid = str(interaction.user.id)

    if uid not in loans or loans[uid].get(item, 0) < amount:
        await interaction.response.send_message(
            "❌ No matching loan found.",
            ephemeral=True
        )
        return

    loans[uid][item] -= amount
    if loans[uid][item] <= 0:
        del loans[uid][item]
    if not loans[uid]:
        del loans[uid]

    save_data(inventory, loans)

    await interaction.response.send_message("✅ Loan paid.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

# ================= RUN =================

bot.run(TOKEN)
