import discord
from discord import app_commands
from discord.ext import commands
import os
import json

GUILD_ID = 192108930388721664
DATA_FILE = "inventory.json"

intents = discord.Intents.default()

class OrderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)

        # FULL WIPE + RESYNC (safe now)
        self.tree.clear_commands(guild=guild)
        await self.tree.sync(guild=guild)

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("✅ Slash commands synced cleanly")

bot = OrderBot()

# ----------------------------
# Utility
# ----------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "weapons": {},
            "armor": {},
            "ammo": {},
            "drugs": {},
            "misc": {},
            "loans": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ----------------------------
# Slash Commands
# ----------------------------

@bot.tree.command(name="setup_inventory", description="Initialize inventory storage")
async def setup_inventory(interaction: discord.Interaction):
    save_data(load_data())
    await interaction.response.send_message(
        "✅ Inventory system initialized",
        ephemeral=True
    )

@bot.tree.command(name="deposit", description="Deposit items into storage")
@app_commands.describe(category="weapon, armor, ammo, drugs, misc", item="Item name", amount="Amount")
async def deposit(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    data = load_data()

    category = category.lower()
    if category not in data:
        await interaction.response.send_message("❌ Invalid category", ephemeral=True)
        return

    data[category][item] = data[category].get(item, 0) + amount
    save_data(data)

    embed = discord.Embed(
        title="📦 Deposit Successful",
        description=f"**{amount}x {item}** added to **{category}**",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="Withdraw items from storage")
async def withdraw(
    interaction: discord.Interaction,
    category: str,
    item: str,
    amount: int
):
    data = load_data()
    category = category.lower()

    if data.get(category, {}).get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock", ephemeral=True)
        return

    data[category][item] -= amount
    save_data(data)

    embed = discord.Embed(
        title="📤 Withdrawal Successful",
        description=f"**{amount}x {item}** removed from **{category}**",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inventory", description="View current inventory")
async def inventory(interaction: discord.Interaction):
    data = load_data()
    embed = discord.Embed(title="📊 Order Inventory", color=discord.Color.blue())

    for category, items in data.items():
        if category == "loans":
            continue
        if not items:
            embed.add_field(name=category.capitalize(), value="Empty", inline=False)
        else:
            text = "\n".join(f"{k}: {v}" for k, v in items.items())
            embed.add_field(name=category.capitalize(), value=text, inline=False)

    await interaction.response.send_message(embed=embed)

# ----------------------------
# Startup
# ----------------------------

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
