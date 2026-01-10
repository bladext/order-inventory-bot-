import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import asyncio

# =====================
# CONFIG
# =====================
GUILD_ID = 192108930388721664
DATA_FILE = "inventory.json"
MESSAGE_FILE = "message.json"

intents = discord.Intents.default()

# =====================
# BOT
# =====================
class OrderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)

        # FULL command reset + sync
        self.tree.clear_commands(guild=guild)
        await self.tree.sync(guild=guild)

        print("✅ Slash commands synced")

bot = OrderBot()

# =====================
# DATA
# =====================
def default_data():
    return {
        "weapons": {},
        "armor": {},
        "ammo": {},
        "drugs": {},
        "misc": {},
        "loans": {}
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(default_data())

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # self-heal categories
    base = default_data()
    for k in base:
        data.setdefault(k, {})

    save_data(data)
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        return None
    with open(MESSAGE_FILE, "r") as f:
        return json.load(f)

def save_message(data):
    with open(MESSAGE_FILE, "w") as f:
        json.dump(data, f)

# =====================
# EMBED
# =====================
def build_inventory_embed(data):
    embed = discord.Embed(
        title="📦 Ørder Inventory",
        color=discord.Color.dark_gold()
    )

    for cat in ["weapons", "armor", "ammo", "drugs", "misc"]:
        items = data[cat]
        value = "Empty" if not items else "\n".join(f"{k}: {v}" for k, v in items.items())
        embed.add_field(name=cat.capitalize(), value=value, inline=False)

    if data["loans"]:
        text = ""
        for user, items in data["loans"].items():
            text += f"**{user}**\n"
            for item, amt in items.items():
                text += f"• {item}: {amt}\n"
        embed.add_field(name="📄 Loans", value=text, inline=False)

    embed.set_footer(text="Auto-updating inventory")
    return embed

async def update_inventory_message(channel):
    data = load_data()
    embed = build_inventory_embed(data)

    saved = load_message()
    if saved:
        try:
            msg = await channel.fetch_message(saved["message_id"])
            await msg.edit(embed=embed)
            return
        except:
            pass

    msg = await channel.send(embed=embed)
    save_message({"channel_id": channel.id, "message_id": msg.id})

# =====================
# CATEGORY DROPDOWN (STRING SAFE)
# =====================
CATEGORY_LIST = ["weapons", "armor", "ammo", "drugs", "misc"]

async def category_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=c.capitalize(), value=c)
        for c in CATEGORY_LIST if current.lower() in c
    ]

# =====================
# COMMANDS
# =====================
@bot.tree.command(name="setup_inventory")
async def setup_inventory(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Inventory system ready", ephemeral=True)
    asyncio.create_task(update_inventory_message(interaction.channel))

@bot.tree.command(name="deposit")
@app_commands.autocomplete(category=category_autocomplete)
async def deposit(interaction: discord.Interaction, category: str, item: str, amount: int):
    data = load_data()

    if category not in data:
        await interaction.response.send_message("❌ Invalid category", ephemeral=True)
        return

    data[category][item] = data[category].get(item, 0) + amount
    save_data(data)

    await interaction.response.send_message(f"📦 Deposited {amount}x {item}", ephemeral=True)
    asyncio.create_task(update_inventory_message(interaction.channel))

@bot.tree.command(name="withdraw")
@app_commands.autocomplete(category=category_autocomplete)
async def withdraw(interaction: discord.Interaction, category: str, item: str, amount: int):
    data = load_data()

    if data[category].get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock", ephemeral=True)
        return

    data[category][item] -= amount
    if data[category][item] == 0:
        del data[category][item]

    save_data(data)
    await interaction.response.send_message(f"📤 Withdrew {amount}x {item}", ephemeral=True)
    asyncio.create_task(update_inventory_message(interaction.channel))

@bot.tree.command(name="loan")
async def loan(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    data = load_data()
    user = str(member)

    data["loans"].setdefault(user, {})
    data["loans"][user][item] = data["loans"][user].get(item, 0) + amount
    save_data(data)

    await interaction.response.send_message(f"📄 Loaned {amount}x {item} to {member.mention}", ephemeral=True)
    asyncio.create_task(update_inventory_message(interaction.channel))

@bot.tree.command(name="pay")
async def pay(interaction: discord.Interaction, item: str, amount: int):
    data = load_data()
    user = str(interaction.user)

    if user not in data["loans"] or data["loans"][user].get(item, 0) < amount:
        await interaction.response.send_message("❌ No such loan", ephemeral=True)
        return

    data["loans"][user][item] -= amount
    if data["loans"][user][item] == 0:
        del data["loans"][user][item]
    if not data["loans"][user]:
        del data["loans"][user]

    save_data(data)
    await interaction.response.send_message(f"✅ Paid back {amount}x {item}", ephemeral=True)
    asyncio.create_task(update_inventory_message(interaction.channel))

# =====================
# START
# =====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
