import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 192108930388721664
STAFF_LOG_CHANNEL_ID = 1459705984657129543
REQUIRED_ROLE = "Hierarchy"

INVENTORY_FILE = "inventory.json"
MESSAGE_FILE = "message.json"

CATEGORIES = ["weapons", "armor", "ammo", "drugs", "misc"]

# ================= BOT SETUP =================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= PERMISSION CHECK =================

def has_hierarchy(interaction: discord.Interaction) -> bool:
    return any(role.name == REQUIRED_ROLE for role in interaction.user.roles)

# ================= FILE HELPERS =================

def load_data():
    if not os.path.exists(INVENTORY_FILE):
        return {c: {} for c in CATEGORIES}, {}
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    return data.get("inventory", {}), data.get("loans", {})

def save_data(inventory, loans):
    with open(INVENTORY_FILE, "w") as f:
        json.dump({"inventory": inventory, "loans": loans}, f, indent=2)

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        return None
    with open(MESSAGE_FILE, "r") as f:
        return json.load(f)

def save_message(data):
    with open(MESSAGE_FILE, "w") as f:
        json.dump(data, f)

# ================= LOGGING =================

async def log_action(guild, message):
    channel = guild.get_channel(STAFF_LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

# ================= EMBED =================

async def update_inventory_embed(guild):
    msg_data = load_message()
    if not msg_data:
        return

    inventory, loans = load_data()
    channel = guild.get_channel(msg_data["channel_id"])
    if not channel:
        return

    message = await channel.fetch_message(msg_data["message_id"])

    embed = discord.Embed(
        title="📦 Ørder Storage",
        color=discord.Color.dark_red()
    )

    # Inventory sections
    for cat in CATEGORIES:
        items = inventory.get(cat, {})
        value = "\n".join(f"• {k}: {v}" for k, v in items.items()) or "—"
        embed.add_field(name=cat.capitalize(), value=value, inline=False)

    # Loans (grouped per user)
    loans_lines = []
    for uid, items in loans.items():
        user_block = [f"<@{uid}>"]
        for item, amt in items.items():
            user_block.append(f"• {amt}x {item}")
        loans_lines.append("\n".join(user_block))

    embed.add_field(
        name="📄 Loans",
        value="\n\n".join(loans_lines) if loans_lines else "—",
        inline=False
    )

    await message.edit(embed=embed)

# ================= EVENTS =================

@bot.event
async def setup_hook():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    await bot.tree.sync(guild=guild)
    print("🔥 GUILD SLASH COMMANDS SYNCED 🔥")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ================= AUTOCOMPLETE =================

async def category_autocomplete(_, current: str):
    return [
        app_commands.Choice(name=c, value=c)
        for c in CATEGORIES
        if current.lower() in c
    ]

# ================= COMMANDS =================

@bot.tree.command(name="inventory", description="View inventory", guild=discord.Object(id=GUILD_ID))
async def inventory(interaction: discord.Interaction):
    await interaction.response.send_message(
        "📦 Inventory is shown above.",
        ephemeral=True
    )

@bot.tree.command(name="setup_inventory", description="Create inventory embed", guild=discord.Object(id=GUILD_ID))
async def setup_inventory(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Ørder Storage", color=discord.Color.dark_red())
    msg = await interaction.channel.send(embed=embed)
    save_message({"channel_id": interaction.channel.id, "message_id": msg.id})
    await interaction.response.send_message("✅ Inventory setup complete.", ephemeral=True)
    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="deposit", guild=discord.Object(id=GUILD_ID))
@app_commands.autocomplete(category=category_autocomplete)
async def deposit(interaction: discord.Interaction, category: str, item: str, amount: int):
    if not has_hierarchy(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    inventory, loans = load_data()
    inventory.setdefault(category, {})
    inventory[category][item] = inventory[category].get(item, 0) + amount
    save_data(inventory, loans)

    await interaction.response.send_message(
        f"✅ Deposited **{amount}x {item}** into **{category}**.",
        ephemeral=True
    )

    await log_action(
        interaction.guild,
        f"📥 Deposit | {interaction.user.mention} added {amount}x {item} ({category})"
    )

    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="pay", guild=discord.Object(id=GUILD_ID))
async def pay(
    interaction: discord.Interaction,
    member: discord.Member,
    item: str,
    amount: int
):
    if not has_hierarchy(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    inventory, loans = load_data()
    user_id = str(member.id)

    if user_id not in loans or item not in loans[user_id]:
        await interaction.response.send_message(
            "❌ That loan does not exist.",
            ephemeral=True
        )
        return

    if amount > loans[user_id][item]:
        await interaction.response.send_message(
            "❌ Cannot pay more than owed.",
            ephemeral=True
        )
        return

    # Deduct from loan
    loans[user_id][item] -= amount
    if loans[user_id][item] <= 0:
        del loans[user_id][item]

    if not loans[user_id]:
        del loans[user_id]

    save_data(inventory, loans)

    await interaction.response.send_message(
        f"✅ **{amount}x {item}** paid back by {member.mention}.",
        ephemeral=True
    )

    await log_action(
        interaction.guild,
        f"💰 Pay | {interaction.user.mention} marked {amount}x {item} as paid by {member.mention}"
    )

    await update_inventory_embed(interaction.guild)


@bot.tree.command(name="withdraw", guild=discord.Object(id=GUILD_ID))
@app_commands.autocomplete(category=category_autocomplete)
async def withdraw(interaction: discord.Interaction, category: str, item: str, amount: int):
    if not has_hierarchy(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    inventory, loans = load_data()
    if inventory.get(category, {}).get(item, 0) < amount:
        await interaction.response.send_message("❌ Not enough stock.", ephemeral=True)
        return

    inventory[category][item] -= amount
    if inventory[category][item] <= 0:
        del inventory[category][item]

    save_data(inventory, loans)

    await interaction.response.send_message(
        f"📤 Withdrew **{amount}x {item}** from **{category}**.",
        ephemeral=True
    )

    await log_action(
        interaction.guild,
        f"📤 Withdraw | {interaction.user.mention} took {amount}x {item} ({category})"
    )

    await update_inventory_embed(interaction.guild)

@bot.tree.command(name="loan", guild=discord.Object(id=GUILD_ID))
async def loan(interaction: discord.Interaction, member: discord.Member, item: str, amount: int):
    if not has_hierarchy(interaction):
        await interaction.response.send_message("❌ No permission.", ephemeral=True)
        return

    inventory, loans = load_data()
    loans.setdefault(str(member.id), {})
    loans[str(member.id)][item] = loans[str(member.id)].get(item, 0) + amount
    save_data(inventory, loans)

    await interaction.response.send_message(
        f"📄 Loaned **{amount}x {item}** to {member.mention}.",
        ephemeral=True
    )

    await log_action(
        interaction.guild,
        f"📄 Loan | {interaction.user.mention} loaned {amount}x {item} to {member.mention}"
    )

    await update_inventory_embed(interaction.guild)

# ================= RUN =================

bot.run(TOKEN)
