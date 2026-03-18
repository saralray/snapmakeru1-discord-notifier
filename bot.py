import os
import json
import asyncio
import discord
import requests
from io import BytesIO
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 20))

PRINTER_FILE = "printers.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def load_printers():
    with open(PRINTER_FILE, "r") as f:
        return json.load(f)


def save_printers(data):
    with open(PRINTER_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# STATE CARD STYLE
# =========================

def build_state_embed(printer_name, printer_url, state, data):
    state = state.upper()
    file = None 

    if state == "PRINTING":
        color = 0x3b82f6
        icon = "▶️"
        label = "STARTED"
    elif state == "COMPLETE":
        color = 0x22c55e
        icon = "✅"
        label = "COMPLETED"
    elif state == "CANCELLED":
        color = 0xef4444
        icon = "❌"
        label = "CANCELLED"
    elif state == "ERROR":
        color = 0xef4444
        icon = "🚨"
        label = "ERROR"
    else:
        color = 0xef4444
        icon = "🔴"
        label = "OFFLINE"

    total_seconds = int(data.get("print_duration", 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    filament = data.get("filament_used", 0) / 1000 * 3
    filename = data.get("filename", "-")

    embed = discord.Embed(
        title=f"Printer {printer_name}  {label}  {icon}",
        color=color
    )

    embed.add_field(
        name="State",
        value=label,
        inline=True
    )

    embed.add_field(
        name="Time",
        value=f"{hours}h {minutes:02d}m",
        inline=True
    )

    embed.add_field(
        name="Filament",
        value=f"{filament:.1f} g",
        inline=True
    )

    if state in ["ERROR","CANCELLED", "COMPLETE"]:
        try:
            response = requests.get(f"{printer_url}/webcam/snapshot.jpg", timeout=5)
            image_bytes = BytesIO(response.content)

            file = discord.File(image_bytes, filename="snapshot.jpg")
            embed.set_image(url="attachment://snapshot.jpg")
        except Exception as e:
            print("Snapshot error:", e)

    embed.add_field(
        name="File",
        value=filename if filename else "-",
        inline=False
    )

    return embed, file


# =========================
# HEX TO COLORED CIRCLE
# =========================

def hex_to_circle(hex_color):
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    if r > 200 and g < 100 and b < 100:
        return "🔴"
    if g > 200 and r < 120:
        return "🟢"
    if b > 200 and r < 120:
        return "🔵"
    if r > 200 and g > 150:
        return "🟡"
    if r > 150 and b > 150:
        return "🟣"
    if r > 150 and g > 80:
        return "🟠"

    return "⚪"


# =========================
# /filament COMMAND
# =========================

@tree.command(
    name="filament",
    description="Show filament status",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(printer="Printer name")
async def filament(interaction: discord.Interaction, printer: str):

    printers = load_printers()
    selected = next((p for p in printers if p["name"] == printer), None)

    if not selected:
        await interaction.response.send_message("Printer not found.")
        return

    await interaction.response.defer()

    try:
        r = requests.get(
            f"{selected['url']}/printer/objects/query?print_task_config",
            timeout=5
        )

        cfg = r.json()["result"]["status"]["print_task_config"]

        embed = discord.Embed(
            title="Filament Lists",
            description=f"**Printer:** {selected['name']}",
            color=0x5865F2  # Lexa-style blue
        )

        for i, ftype in enumerate(cfg["filament_type"]):
            hex_color = cfg["filament_color_rgba"][i][:6]
            circle = hex_to_circle(hex_color)
            loaded = cfg["filament_exist"][i]

            status = "**Loaded**" if loaded else "**Empty**"

            embed.add_field(
                name=f"Slot {i+1} {circle}",
                value=(
                    f"{ftype}\n"
                    f"{status}"
                ),
                inline=True
            )

        embed.set_footer(text="Snapmaker U1")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")


@filament.autocomplete("printer")
async def printer_autocomplete(interaction: discord.Interaction, current: str):
    printers = load_printers()
    return [
        app_commands.Choice(name=p["name"], value=p["name"])
        for p in printers if current.lower() in p["name"].lower()
    ]


# =========================
# MONITOR PRINTER STATE
# =========================

async def monitor_printers():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        printers = load_printers()

        for printer in printers:
            try:
                r = requests.get(
                    f"{printer['url']}/printer/objects/query?print_stats",
                    timeout=5
                )
                data = r.json()["result"]["status"]["print_stats"]
                state = data.get("state", "OFFLINE")
            except:
                state = "OFFLINE"
                data = {}

            if printer["last_state"] != state:
                embed, file = build_state_embed(
                    printer["name"],
                    printer["url"],
                    state,
                    data
                )
                if file:
                    await channel.send(embed=embed, file=file)
                else:
                    await channel.send(embed=embed)
                printer["last_state"] = state

        save_printers(printers)
        await asyncio.sleep(POLL_INTERVAL)


# =========================
# STARTUP
# =========================

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild)
    print(f"Bot ready as {client.user}")
    client.loop.create_task(monitor_printers())


client.run(TOKEN)