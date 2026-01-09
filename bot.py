import os
import json
import logging
import discord
from discord import app_commands
from discord.ext import commands

# --------------------
# CONFIG
# --------------------
GUILD_ID = 192108930388721664
DATA_FILE = "inventory.json"

logging.basicConfig(level=logging.INFO)

# --------------------
# BOT SETUP
# --------------------
intents = discord.Intents.default()
intents.members = True

class OrderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

   async def setup_hook(self):
    guild = discord.Object(id=192108930388721664)

    # DELETE all existing commands (this is the fix)
    self.tree.clear_commands(guild=guild)
    await self.tree.sync(guild=guild)

    print("🔥 Old slash commands nuked")

    # Re-sync fresh commands
    await self.tree.sync(guild=guild)
    print("✅ Fresh slash commands synced")


bot = OrderBot()

TOKEN = os.getenv("DISCORD_TOKEN")

# --------------------
# DATA
# --------------------
def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------------------
# INVENTORY DISPLAY
# --------------------
def format_category(items):
    if not items:
        return "Empty"
    return "\n".join(f"• **{k}**: {v}" for k, v in items.items())

async def update_inventory_message():
    data = load_data()
    if not data["message_id"]:
        return

    channel = bot.get_channel(data["channel_id"])
    msg = await channel.fetch_message(data["message_id"])

    embed = discord.Embed(
        title="Ørder Inventory",
        description="Live gang inventory tracking",
        color=discord.Color.dark_grey()
    )

    inv = data["inventory"]
    embed.add_field(name="🔫 Weapons", v_
