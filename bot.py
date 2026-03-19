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


# =========================
# FILE HANDLING
# =========================

def load_printers():
    with open(PRINTER_FILE, "r") as f:
        data = json.load(f)
        return sorted(data, key=lambda p: p["name"].lower())


def save_printers(data):
    with open(PRINTER_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# NETWORK (NON-BLOCKING REQUESTS)
# =========================

async def fetch_json(url, headers):
    def _get():
        return requests.get(url, headers=headers, timeout=5)

    for _ in range(2):
        try:
            r = await asyncio.to_thread(_get)
            return r.json()
        except:
            await asyncio.sleep(1)
    return {}


async def fetch_snapshot(url, api_key):
    def _get():
        return requests.get(
            f"{url}/webcam/snapshot.jpg",
            headers={"X-Api-Key": api_key},
            timeout=5
        )
    return await asyncio.to_thread(_get)


# =========================
# STATE EMBED
# =========================

async def build_state_embed(printer_name, printer_url, api_key, state, data):
    state = state.upper()
    file = None

    total_seconds = int(data.get("print_duration", 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    filament = data.get("filament_used", 0) / 1000
    filename = data.get("filename") or "-"

    config = {
        "PRINTING":  ("STARTED", 0x3b82f6),
        "COMPLETE":  ("COMPLETED", 0x22c55e),
        "CANCELLED": ("CANCELLED", 0xef4444),
        "ERROR":     ("ERROR", 0xef4444),
        "PAUSED":    ("PAUSED", 0xfacc15),
        "OFFLINE":   ("OFFLINE", 0xef4444),
    }

    label, color = config.get(state, config["OFFLINE"])

    embed = discord.Embed(
        title=f"Printer {printer_name} — {label}",
        color=color
    )

    if state == "PRINTING":
        embed.add_field(name="File", value=filename, inline=False)

        progress = data.get("progress")
        if progress is not None:
            embed.add_field(
                name="Progress",
                value=f"{progress * 100:.1f}%",
                inline=False
            )

    elif state in ["COMPLETE", "CANCELLED", "ERROR"]:
        embed.add_field(name="Time", value=f"{hours}h {minutes:02d}m", inline=True)
        embed.add_field(name="Filament", value=f"{filament:.1f} m", inline=True)
        embed.add_field(name="File", value=filename, inline=False)

        # ===== OLD IMAGE SYSTEM (kept) =====
        try:
            response = await fetch_snapshot(printer_url, api_key)

            if response.status_code == 200:
                image_bytes = BytesIO(response.content)
                file = discord.File(image_bytes, filename="snapshot.jpg")
                embed.set_image(url="attachment://snapshot.jpg")

        except Exception as e:
            print("Snapshot error:", e)

    return embed, file


# =========================
# HEX → LABEL (NO EMOJI)
# =========================

def hex_to_label(hex_color):
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    if r > 200 and g < 100:
        return "🔴"
    if g > 200:
        return "🟢"
    if b > 200:
        return "🔵"
    if r > 200 and g > 150:
        return "🟡"
    if r > 150 and b > 150:
        return "🟣"
    if r > 150 and g > 80:
        return "🟠"

    return "⚪"


# =========================
# /filament
# =========================

@tree.command(name="filament", description="Show filament status", guild=discord.Object(id=GUILD_ID))
async def filament(interaction: discord.Interaction, printer: str):

    printers = load_printers()
    selected = next((p for p in printers if p["name"] == printer), None)

    if not selected:
        await interaction.response.send_message("Printer not found.")
        return

    await interaction.response.defer()

    try:
        r = await fetch_json(
            f"{selected['url']}/printer/objects/query?print_task_config",
            headers={"X-Api-Key": selected["api_key"]}
        )

        cfg = r.get("result", {}).get("status", {}).get("print_task_config", {})

        filament_types = cfg.get("filament_type", [])
        colors = cfg.get("filament_color_rgba", [])
        exists = cfg.get("filament_exist", [])

        embed = discord.Embed(
            title="Filament Lists",
            description=f"Printer: {selected['name']}",
            color=0x5865F2
        )

        for i, ftype in enumerate(filament_types):
            hex_color = colors[i][:6] if i < len(colors) else "FFFFFF"
            label = hex_to_label(hex_color)
            loaded = exists[i] if i < len(exists) else False

            status = "Loaded" if loaded else "Empty"
            
            if not loaded:
                embed.add_field(
                    name=f"Slot {i+1}",
                    value=f"{ftype}\n{status}",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"Slot {i+1}",
                    value=f"{ftype}({label})\n{status}",
                    inline=True
                )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")


# =========================
# ADD / REMOVE
# =========================

@tree.command(name="addprinter", description="Add printer", guild=discord.Object(id=GUILD_ID))
async def add_printer(interaction: discord.Interaction, name: str, ip: str, api_key: str):
    printers = load_printers()

    if any(p["name"] == name for p in printers):
        await interaction.response.send_message("Printer already exists.")
        return

    printers.append({
        "name": name,
        "url": "http://" + ip,
        "api_key": api_key,
        "last_state": "UNKNOWN"
    })

    save_printers(printers)
    await interaction.response.send_message(f"Printer added: {name} ({ip})")


@tree.command(name="removeprinter", description="Remove printer", guild=discord.Object(id=GUILD_ID))
async def remove_printer(interaction: discord.Interaction, printer: str):
    printers = load_printers()
    updated = [p for p in printers if p["name"] != printer]

    if len(updated) == len(printers):
        await interaction.response.send_message("Printer not found.")
        return

    save_printers(updated)
    await interaction.response.send_message(f"Printer removed: {printer}")


# =========================
# AUTOCOMPLETE
# =========================

@filament.autocomplete("printer")
async def auto1(interaction, current):
    return [
        app_commands.Choice(name=p["name"], value=p["name"])
        for p in load_printers()
        if current.lower() in p["name"].lower()
    ]


@remove_printer.autocomplete("printer")
async def auto2(interaction, current):
    return [
        app_commands.Choice(name=p["name"], value=p["name"])
        for p in load_printers()
        if current.lower() in p["name"].lower()
    ]


# =========================
# MONITOR LOOP
# =========================

async def monitor_printers():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)

    first_run = True

    while not client.is_closed():
        printers = load_printers()

        for printer in printers:
            try:
                r = await fetch_json(
                    f"{printer['url']}/printer/objects/query?print_stats",
                    headers={"X-Api-Key": printer["api_key"]}
                )

                data = r.get("result", {}).get("status", {}).get("print_stats", {})
                state = data.get("state", "OFFLINE")

            except:
                state = "OFFLINE"
                data = {}

            if not first_run and printer.get("last_state") != state:
                embed, file = await build_state_embed(
                    printer["name"],
                    printer["url"],
                    printer["api_key"],
                    state,
                    data
                )

                if file:
                    await channel.send(embed=embed, file=file)
                else:
                    await channel.send(embed=embed)

            printer["last_state"] = state

        save_printers(printers)
        first_run = False
        await asyncio.sleep(POLL_INTERVAL)


# =========================
# STARTUP
# =========================

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot ready as {client.user}")
    client.loop.create_task(monitor_printers())


client.run(TOKEN)