import os
import json
import logging
import discord
from discord.ext import commands
logging.basicConfig(level=logging.INFO)
print("Bot file loaded")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

TOKEN = os.getenv("DISCORD_TOKEN")
print("Token loaded:", "YES" if TOKEN else "NO")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing!")

bot.run(TOKEN)

