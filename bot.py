import discord
from discord import app_commands
from discord.ext import commands
import os
import json

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

        # Clear any ghost commands and resync cleanly
        self.tree.clear_commands(guild=guild)
        await self.tree.sync(guild=guild)

        print("✅ Slash commands synced cleanly")

bot = OrderBot()

# =====================
# DATA HANDLING
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
        return json.load(f)

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
# EMBED BUILDER
# =====================
def build_inventory_embed(data):
    embed = discord.Embed(
        title="📦 Ørder Inventory",
        color=discord.Color.dark_gold()
    )

    for category in ["weapons", "armor", "ammo", "drugs", "misc"]:
        items = data[category]
        value = "Empty" if not items else "\n".join(f"{k}: {v}" for k, v in items.items())
        embed.add_field(name=category.capitalize(), value=value, inline=False)

    if data["loans"]:
        loan_text = ""
        for user, items in data["loans"].items():
            loan_text += f"**{user}**\n"
            for item, amt in items.items():
                loan_text += f"• {item}: {amt}\n"
        embed.add_field(name="📄 Loans", value=loan_text, inline=False)

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
# COMMAND CHOICES
# =====================
CATEGORY_CHOICES = [
    app_commands.Choice(name="Weapons", value="weapons"),
    app_commands.Choice(name="Armor", value="armor"),
    app_commands.Choice(name="Ammo", value="ammo"),
    app_commands.Choice(name="Drugs", value="drugs"),
    app_commands.Choice(name="Misc", value="misc"),
]

# =====================
# SLASH COMMANDS
# =====================
@bot.tree.command(name="setup_inventory", description="Create the persistent inventory message")
async def setup_inventory(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await update_inventory_message(interaction.channel)
    await interaction.followup.send("✅ Inventory message created")

@bot.tree.command(name="deposit", description="Deposit items")
@app_commands.choices(category=CATEGORY_CHOICES)
async def deposit(interaction: discord.Interaction, category: app_commands.Choice[str], item: str, amount: int):
    await interaction.response.defer(ephemeral=True)

    data = load_data()
    cat = category.value
    data[cat][item] = data[cat].get(item, 0) + amount
    save_data(data)

    await update_inventory_message(interaction.channel)
    await interaction.followup.send(f"📦 Deposited {amount}x {item}")

@bot.tree.command(name="withdraw", description="Withdraw items")
@app_commands.choices(category=CATEGORY_CHOICES)
async def withdraw(interaction: discord.Interaction, category: app_commands.Choice[str], item: str, amount: int):
    await interaction.response.defer(ephemeral=True)

    data = load_data()
    cat = category.value

    if data[cat].get(item, 0) < amount:
        await interaction.followup.send("❌ Not enough stock")
        return

    data[cat][item] -= amount
    if data[cat][item] == 0:
        del data[cat][item]

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.followup.send(f"📤 Withdrew {amount}x {item}")

@bot.tree.command(name="loan", description="Loan items to a member")
async def loan(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    await interaction.response.defer(ephemeral=True)

    data = load_data()
    user = str(member)

    data["loans"].setdefault(user, {})
    data["loans"][user][item] = data["loans"][user].get(item, 0) + amount

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.followup.send(f"📄 Loaned {amount}x {item} to {member.mention}")

@bot.tree.command(name="pay", description="Pay back loaned items")
async def pay(interaction: discord.Interaction, item: str, amount: int):
    await interaction.response.defer(ephemeral=True)

    data = load_data()
    user = str(interaction.user)

    if user not in data["loans"] or data["loans"][user].get(item, 0) < amount:
        await interaction.followup.send("❌ No such loan")
        return

    data["loans"][user][item] -= amount
    if data["loans"][user][item] == 0:
        del data["loans"][user][item]
    if not data["loans"][user]:
        del data["loans"][user]

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.followup.send(f"✅ Paid back {amount}x {item}")

# =====================
# START BOT
# =====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
