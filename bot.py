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
DATA_FILE = "inventory.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")
    
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_inventory(ctx):
    data = load_data()

    embed = discord.Embed(
        title="Ørder Inventory",
        description="Live gang inventory tracking",
        color=discord.Color.dark_grey()
    )

    embed.add_field(name="Weapons", value="Empty", inline=False)
    embed.add_field(name="Armor", value="Empty", inline=False)
    embed.add_field(name="Ammo", value="Empty", inline=False)
    embed.add_field(name="Drugs", value="Empty", inline=False)
    embed.add_field(name="Misc", value="Empty", inline=False)
    embed.add_field(name="Loans", value="None", inline=False)

    msg = await ctx.send(embed=embed)

    data["message_id"] = msg.id
    data["channel_id"] = ctx.channel.id
    save_data(data)

    await ctx.send("✅ Inventory message created.", delete_after=5)
    await ctx.message.delete()


# --------------------
# Run bot
# --------------------
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing!")

bot.run(TOKEN)
