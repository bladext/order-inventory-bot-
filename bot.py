import os
import json
import logging
import discord
from discord.ext import commands

# --------------------
# Logging
# --------------------
logging.basicConfig(level=logging.INFO)
print("Bot file loaded")

# --------------------
# Bot setup (MUST COME BEFORE EVENTS)
# --------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --------------------
# Environment
# --------------------
TOKEN = os.getenv("DISCORD_TOKEN")
print("Token loaded:", "YES" if TOKEN else "NO")

# --------------------
# Events
# --------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

# --------------------
# Run bot
# --------------------
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing!")

bot.run(TOKEN)
