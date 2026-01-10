import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    # GLOBAL command sync ONLY
    await bot.tree.sync()
    print("✅ Global slash commands synced")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for g in bot.guilds:
        print("Connected to:", g.name, g.id)

@bot.tree.command(name="ping", description="Test command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

bot.run(TOKEN)
