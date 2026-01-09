import os
import json
import logging
import discord
from discord import app_commands
from discord.ext import commands

# --------------------
# Logging
# --------------------
logging.basicConfig(level=logging.INFO)

# --------------------
# Bot setup
# --------------------
intents = discord.Intents.default()
intents.members = True

class OrderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced")

bot = OrderBot()

# --------------------
# Environment
# --------------------
TOKEN = os.getenv("DISCORD_TOKEN")

# --------------------
# Data
# --------------------
DATA_FILE = "inventory.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------------------
# Helpers
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
    embed.add_field(name="🔫 Weapons", value=format_category(inv["weapon"]), inline=False)
    embed.add_field(name="🛡️ Armor", value=format_category(inv["armor"]), inline=False)
    embed.add_field(name="🔋 Ammo", value=format_category(inv["ammo"]), inline=False)
    embed.add_field(name="💊 Drugs", value=format_category(inv["drugs"]), inline=False)
    embed.add_field(name="📦 Misc", value=format_category(inv["misc"]), inline=False)

    loans = data["loans"]
    loan_text = (
        "\n".join(
            f"• **{user}**: {', '.join(f'{i} x{a}' for i, a in items.items())}"
            for user, items in loans.items()
        ) if loans else "None"
    )

    embed.add_field(name="📄 Loans", value=loan_text, inline=False)
    await msg.edit(embed=embed)

# --------------------
# Events
# --------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --------------------
# Slash Commands
# --------------------
@bot.tree.command(name="setup_inventory", description="Create the inventory board")
@app_commands.checks.has_permissions(administrator=True)
async def setup_inventory(interaction: discord.Interaction):
    data = load_data()

    embed = discord.Embed(
        title="Ørder Inventory",
        description="Live gang inventory tracking",
        color=discord.Color.dark_grey()
    )

    for name in ["Weapons", "Armor", "Ammo", "Drugs", "Misc", "Loans"]:
        embed.add_field(name=name, value="Empty", inline=False)

    msg = await interaction.channel.send(embed=embed)

    data["message_id"] = msg.id
    data["channel_id"] = interaction.channel.id
    save_data(data)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Inventory Created",
            description="This message will now auto-update.",
            color=discord.Color.green()
        ),
        ephemeral=True
    )

@bot.tree.command(name="deposit", description="Deposit items into inventory")
@app_commands.choices(category=[
    app_commands.Choice(name="Weapon", value="weapon"),
    app_commands.Choice(name="Armor", value="armor"),
    app_commands.Choice(name="Ammo", value="ammo"),
    app_commands.Choice(name="Drugs", value="drugs"),
    app_commands.Choice(name="Misc", value="misc")
])
async def deposit(interaction: discord.Interaction, category: app_commands.Choice[str], item: str, amount: int):
    data = load_data()
    inv = data["inventory"][category.value]
    inv[item] = inv.get(item, 0) + amount
    save_data(data)

    await update_inventory_message()
    await interaction.response.send_message(
        embed=discord.Embed(
            title="📦 Deposit Successful",
            description=f"**{item}** x{amount}",
            color=discord.Color.green()
        ),
        ephemeral=True
    )

@bot.tree.command(name="withdraw", description="Withdraw items from inventory")
async def withdraw(interaction: discord.Interaction, category: str, item: str, amount: int):
    data = load_data()
    inv = data["inventory"].get(category)

    if not inv or item not in inv or inv[item] < amount:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Withdraw Failed",
                description="Not enough inventory.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    inv[item] -= amount
    if inv[item] <= 0:
        del inv[item]

    save_data(data)
    await update_inventory_message()

    await interaction.response.send_message(
        embed=discord.Embed(
            title="📤 Withdraw Successful",
            description=f"**{item}** x{amount}",
            color=discord.Color.orange()
        ),
        ephemeral=True
    )

@bot.tree.command(name="loan", description="Loan items to a member")
async def loan(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    data = load_data()
    user = str(member)
    loans = data["loans"].setdefault(user, {})
    loans[item] = loans.get(item, 0) + amount
    save_data(data)

    await update_inventory_message()
    await interaction.response.send_message(
        embed=discord.Embed(
            title="📄 Loan Recorded",
            description=f"{member.display_name} borrowed **{item} x{amount}**",
            color=discord.Color.blurple()
        ),
        ephemeral=True
    )

@bot.tree.command(name="pay", description="Pay back loaned items")
async def pay(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    data = load_data()
    user = str(member)
    loans = data["loans"].get(user)

    if not loans or item not in loans or loans[item] < amount:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Payment Failed",
                description="Loan not found or invalid amount.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    loans[item] -= amount
    if loans[item] <= 0:
        del loans[item]
    if not loans:
        del data["loans"][user]

    save_data(data)
    await update_inventory_message()
    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Loan Paid",
            description=f"{member.display_name} repaid **{item} x{amount}**",
            color=discord.Color.green()
        ),
        ephemeral=True
    )

# --------------------
# Run
# --------------------
bot.run(TOKEN)
