import json
import os
import time
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
PRINTER_FILE = "printers.json"
MAX_WORKERS = 10

STATUS_STYLE = {
    "offline":   {"color": 0xED4245, "icon": "🔴", "label": "OFFLINE"},
    "printing":  {"color": 0x5865F2, "icon": "▶️", "label": "STARTED"},
    "complete":  {"color": 0x57F287, "icon": "✅", "label": "COMPLETED"},
    "cancelled": {"color": 0xED4245, "icon": "❌", "label": "CANCELLED"},
    "idle":      {"color": 0xAAAAAA, "icon": "⏸️", "label": "IDLE"}
}

def load_printers():
    if not os.path.exists(PRINTER_FILE):
        return []
    with open(PRINTER_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_printers(printers):
    with open(PRINTER_FILE, "w", encoding="utf-8") as f:
        json.dump(printers, f, indent=2, ensure_ascii=False)

def send_discord_embed(printer, status, job):
    style = STATUS_STYLE.get(status, STATUS_STYLE["offline"])

    embed = {
        "title": f"{printer['name']} {style['icon']} {style['label']}",
        "color": style["color"],
        "fields": [
            {"name": "State", "value": style["label"], "inline": True},
            {"name": "Time", "value": job["time"], "inline": True},
            {"name": "Filament", "value": job["filament"], "inline": True},
            {"name": "File", "value": job["file"], "inline": False}
        ]
    }

    payload = {
        "username": "Snapmaker-U1",
        "embeds": [embed]
    }

    requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)

def seconds_to_hm(seconds):
    if seconds is None:
        return "-"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"

def mm_to_m(mm):
    if mm is None:
        return "-"
    return f"{mm / 1000:.1f} m"

def check_printer(printer):
    try:
        r = requests.get(
            f"http://{printer['ip']}/printer/objects/query?print_stats",
            timeout=5
        )
        data = r.json()["result"]["status"]["print_stats"]

        state = data.get("state", "idle")

        if state == "printing":
            status = "printing"
        elif state == "complete":
            status = "complete"
        elif state == "cancelled":
            status = "cancelled"
        else:
            status = "idle"

        job = {
            "file": data.get("filename", "-"),
            "time": seconds_to_hm(data.get("print_duration")),
            "filament": mm_to_m(data.get("filament_used"))
        }

        if printer.get("last_status") != status:
            send_discord_embed(printer, status, job)
            printer["last_status"] = status

    except Exception:
        if printer.get("last_status") != "offline":
            send_discord_embed(
                printer,
                "offline",
                {"file": "-", "time": "-", "filament": "-"}
            )
            printer["last_status"] = "offline"

def main():
    print("Snapmaker U1 Discord notifier running (Moonraker)")
    while True:
        printers = load_printers()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(check_printer, printers)

        save_printers(printers)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
