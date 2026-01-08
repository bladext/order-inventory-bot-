import os
import json
import logging
import discord
from discord.ext import commands
logging.basicConfig(level=logging.INFO)
print("Bot file loaded")

TOKEN = os.getenv("DISCORD_TOKEN")
print("Token loaded:", "YES" if TOKEN else "NO")


TOKEN = os.getenv("DISCORD_TOKEN")
