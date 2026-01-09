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
# Bot setup
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
# Data handling
# --------------------
DATA_FILE = "inventory.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------------------
# Inventory helpers
# --------------------
def format_category(items):
    if not items:
        return "Empty"
    return "\n".join(f"• **{k}**: {v}" for k, v in items.items())

async def update_inventory_message(bot):
    data = load_data()

    if not data["message_id"] or not data["channel_id"]:
        return

    channel = bot.get_channel(data["channel_id"])
    if not channel:
        return

    msg = await channel.fetch_message(data["message_id"])

    embed = discord.Embed(
        title="Ørder Inventory",
        description="Live gang inventory tracking",
        color=discord.Color.dark_grey()
    )

    inv = data["inventory"]

    embed.add_field(name="Weapons", value=format_category(inv["weapon"]), inline=False)
    embed.add_field(name="Armor", value=format_category(inv["armor"]), inline=False)
    embed.add_field(name="Ammo", value=format_category(inv["ammo"]), inline=False)
    embed.add_field(name="Drugs", value=format_category(inv["drugs"]), inline=False)
    embed.add_field(name="Misc", value=format_category(inv["misc"]), inline=False)

    loans = data["loans"]
    if loans:
        loan_text = "\n".join(
            f"• **{user}**: {', '.join(f'{item} x{amt}' for item, amt in items.items())}"
            for user, items in loans.items()
        )
    else:
        loan_text = "None"

    embed.add_field(name="Loans", value=loan_text, inline=False)

    await msg.edit(embed=embed)

# --------------------
# Events
# --------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

# --------------------
# Commands
# --------------------
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!", delete_after=5)
    await ctx.message.delete()

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

@bot.command()
async def deposit(ctx, category: str, item: str, amount: int):
    category = category.lower()
    if category not in ["weapon", "armor", "ammo", "drugs", "misc"]:
        await ctx.send("❌ Invalid category.", delete_after=5)
        await ctx.message.delete()
        return

    data = load_data()
    inv = data["inventory"][category]

    inv[item] = inv.get(item, 0) + amount

    save_data(data)
    await update_inventory_message(bot)

    await ctx.message.delete()

@bot.command()
async def withdraw(ctx, category: str, item: str, amount: int):
    category = category.lower()
    data = load_data()
    inv = data["inventory"].get(category)

    if not inv or item not in inv or inv[item] < amount:
        await ctx.send("❌ Not enough inventory.", delete_after=5)
        await ctx.message.delete()
        return

    inv[item] -= amount
    if inv[item] <= 0:
        del inv[item]

    save_data(data)
    await update_inventory_message(bot)

    await ctx.message.delete()

# --------------------
# Run bot
# --------------------
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing!")

bot.run(TOKEN)
