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
# GLOBAL CACHE (IMPORTANT)
# =========================
printers_cache = []
session = requests.Session()


# =========================
# FILE HANDLING (OPTIMIZED)
# =========================

def load_printers():
    global printers_cache
    with open(PRINTER_FILE, "r") as f:
        printers_cache = sorted(json.load(f), key=lambda p: p["name"].lower())
    return printers_cache


def save_printers():
    with open(PRINTER_FILE, "w") as f:
        json.dump(printers_cache, f, indent=2)


# =========================
# NETWORK (FASTER)
# =========================

async def fetch_json(url, headers):
    def _get():
        return session.get(url, headers=headers, timeout=5)

    for _ in range(2):
        try:
            r = await asyncio.to_thread(_get)
            return r.json()
        except Exception:
            await asyncio.sleep(1)
    return {}


async def fetch_snapshot(url, api_key):
    def _get():
        return session.get(
            f"{url}/webcam/snapshot.jpg",
            headers={"X-Api-Key": api_key},
            timeout=5
        )
    return await asyncio.to_thread(_get)


# =========================
# EMBED BUILDER (CLEANED)
# =========================

async def build_state_embed(name, url, api_key, state, data):
    state = state.upper()
    file = None

    duration = int(data.get("print_duration", 0))
    hours, minutes = divmod(duration, 3600)
    minutes //= 60

    filament = data.get("filament_used", 0) / 1000 * 3
    filename = data.get("filename") or "-"

    config = {
        "PRINTING": ("STARTED", 0x3b82f6),
        "COMPLETE": ("COMPLETED", 0x22c55e),
        "CANCELLED": ("CANCELLED", 0xef4444),
        "ERROR": ("ERROR", 0xef4444),
        "PAUSED": ("PAUSED", 0xfacc15),
        "OFFLINE": ("OFFLINE", 0xef4444),
        "ONLINE": ("ONLINE", 0x22c55e),
    }

    label, color = config.get(state, config["OFFLINE"])

    embed = discord.Embed(
        title=f"Printer {name} — {label}",
        color=color
    )

    if state == "PRINTING":
        embed.add_field(name="File", value=filename, inline=False)
        progress = data.get("progress")
        if progress is not None:
            embed.add_field(name="Progress", value=f"{progress * 100:.1f}%", inline=False)

    elif state in {"COMPLETE", "CANCELLED", "ERROR"}:
        embed.add_field(name="Time", value=f"{hours}h {minutes:02d}m", inline=True)
        embed.add_field(name="Filament", value=f"{filament:.1f} g", inline=True)
        embed.add_field(name="File", value=filename, inline=False)

        try:
            res = await fetch_snapshot(url, api_key)
            if res.status_code == 200:
                file = discord.File(BytesIO(res.content), filename="snapshot.jpg")
                embed.set_image(url="attachment://snapshot.jpg")
        except Exception as e:
            print("Snapshot error:", e)

    return embed, file


# =========================
# HELPER
# =========================

async def send_embed(channel, embed, file):
    if file:
        await channel.send(embed=embed, file=file)
    else:
        await channel.send(embed=embed)


# =========================
# HEX → LABEL (UNCHANGED)
# =========================

def hex_to_label(hex_color):
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

    if r > 200 and g < 100: return "🔴"
    if g > 200: return "🟢"
    if b > 200: return "🔵"
    if r > 200 and g > 150: return "🟡"
    if r > 150 and b > 150: return "🟣"
    if r > 150 and g > 80: return "🟠"
    return "⚪"


# =========================
# COMMANDS (MINOR CLEANUP)
# =========================

@tree.command(name="filament", description="Show filament status", guild=discord.Object(id=GUILD_ID))
async def filament(interaction: discord.Interaction, printer: str):

    selected = next((p for p in printers_cache if p["name"] == printer), None)

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
        embed = discord.Embed(
            title="Filament Lists",
            description=f"Printer: {selected['name']}",
            color=0x5865F2
        )

        for i, ftype in enumerate(cfg.get("filament_type", [])):
            hex_color = cfg.get("filament_color_rgba", ["FFFFFF"])[i][:6]
            label = hex_to_label(hex_color)
            loaded = cfg.get("filament_exist", [False])[i]

            status = "Loaded" if loaded else "Empty"
            value = f"{ftype}({label})\n{status}" if loaded else f"{ftype}\n{status}"

            embed.add_field(name=f"Slot {i+1}", value=value, inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")


# =========================
# MONITOR LOOP (OPTIMIZED)
# =========================

async def monitor_printers():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)

    first_run = True

    while not client.is_closed():
        for printer in printers_cache:
            try:
                r = await fetch_json(
                    f"{printer['url']}/printer/objects/query?print_stats",
                    headers={"X-Api-Key": printer["api_key"]}
                )
                data = r.get("result", {}).get("status", {}).get("print_stats", {})
                state = data.get("state", "UNKNOWN")

            except Exception:
                state, data = "UNKNOWN", {}

            last_state = printer.get("last_state", "UNKNOWN")

            if not first_run and state != last_state:

                # OFFLINE
                if state == "UNKNOWN":
                    await channel.send(embed=discord.Embed(
                        title=f"Printer {printer['name']} OFFLINE",
                        description="Connection lost",
                        color=0xef4444
                    ))

                # ONLINE
                elif last_state == "UNKNOWN":
                    await channel.send(embed=discord.Embed(
                        title=f"Printer {printer['name']} ONLINE",
                        description="Connection restored",
                        color=0x22c55e
                    ))

                embed, file = await build_state_embed(
                    printer["name"], printer["url"], printer["api_key"], state, data
                )
                await send_embed(channel, embed, file)

            printer["last_state"] = state

        save_printers()
        first_run = False
        await asyncio.sleep(POLL_INTERVAL)


# =========================
# STARTUP
# =========================

@client.event
async def on_ready():
    load_printers()
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot ready as {client.user}")
    client.loop.create_task(monitor_printers())


client.run(TOKEN)