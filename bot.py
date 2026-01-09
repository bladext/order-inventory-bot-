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

        # wipe old commands & resync clean
        self.tree.clear_commands(guild=guild)
        await self.tree.sync(guild=guild)

        await self.tree.sync(guild=guild)
        print("✅ Slash commands synced")

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
        loans_text = ""
        for user, items in data["loans"].items():
            loans_text += f"**{user}**\n"
            for item, amt in items.items():
                loans_text += f"• {item}: {amt}\n"
        embed.add_field(name="📄 Loans", value=loans_text, inline=False)

    embed.set_footer(text="Inventory auto-updates")
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
# COMMANDS
# =====================
CATEGORY_CHOICES = [
    app_commands.Choice(name="Weapons", value="weapons"),
    app_commands.Choice(name="Armor", value="armor"),
    app_commands.Choice(name="Ammo", value="ammo"),
    app_commands.Choice(name="Drugs", value="drugs"),
    app_commands.Choice(name="Misc", value="misc"),
]

@bot.tree.command(name="setup_inventory", description="Create the persistent inventory message")
async def setup_inventory(interaction: discord.Interaction):
    await update_inventory_message(interaction.channel)
    await interaction.response.send_message("✅ Inventory message created", ephemeral=True)

@bot.tree.command(name="deposit", description="Deposit items")
@app_commands.choices(category=CATEGORY_CHOICES)
async def deposit(interaction: discord.Interaction, category: app_commands.Choice[str], item: str, amount: int):
    data = load_data()
    cat = category.value
    data[cat][item] = data[cat].get(item, 0) + amount
    save_data(data)

    await update_inventory_message(interaction.channel)
    await interaction.response.send_message(f"📦 Deposited {amount}x {item}", ephemeral=True)

@bot.tree.command(name="withdraw", description="Withdraw items")
@app_commands.choices(category=CATEGORY_CHOICES)
async def withdraw(interaction: discord.Interaction, category: app_commands.Choice[str], item: str, amount: int):
    data = load_data()
    cat = category.value

    if data[cat].get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock", ephemeral=True)
        return

    data[cat][item] -= amount
    if data[cat][item] == 0:
        del data[cat][item]

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.response.send_message(f"📤 Withdrew {amount}x {item}", ephemeral=True)

@bot.tree.command(name="loan", description="Loan items to a member")
async def loan(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    data = load_data()
    user = str(member)

    data["loans"].setdefault(user, {})
    data["loans"][user][item] = data["loans"][user].get(item, 0) + amount

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.response.send_message(f"📄 Loaned {amount}x {item} to {member.mention}", ephemeral=True)

@bot.tree.command(name="pay", description="Pay back loaned items")
async def pay(interaction: discord.Interaction, item: str, amount: int):
    data = load_data()
    user = str(interaction.user)

    if user not in data["loans"] or data["loans"][user].get(item, 0) < amount:
        await interaction.response.send_message("❌ No such loan", ephemeral=True)
        return

    data["loans"][user][item] -= amount
    if data["loans"][user][item] == 0:
        del data["loans"][user][item]
    if not data["loans"][user]:
        del data["loans"][user]

    save_data(data)
    await update_inventory_message(interaction.channel)
    await interaction.response.send_message(f"✅ Paid back {amount}x {item}", ephemeral=True)

# =====================
# STARTUP
# =====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

bot.run(TOKEN)
