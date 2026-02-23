# snapmakeru1-discord-notifier
Snapmaker U1 Discord Notifier

A lightweight Python service that monitors Snapmaker U1 (Klipper/Moonraker) printers and sends automatic status notifications to Discord using webhooks.

It detects:

🟢 Print Started

✅ Print Completed

❌ Print Cancelled

⏸️ Idle

🔴 Offline

Notifications are sent only when the printer status changes (no spam).

✨ Features

Supports multiple printers

Parallel status checking (multi-threaded)

Discord rich embed messages

Offline detection

Docker support

Configurable polling interval

📦 Requirements

Python 3.9+

Moonraker API enabled on your printer

Discord Webhook URL

🔧 Installation (Local Python)
1. Clone the repository
git clone https://github.com/yourusername/snapmakeru1-discord-notifier.git
cd snapmakeru1-discord-notifier
2. Install dependencies
pip install -r requirements.txt
3. Create .env file
DISCORD_WEBHOOK=https://discord.com/api/webhooks/XXXXXXXX
POLL_INTERVAL=30

DISCORD_WEBHOOK → Your Discord webhook URL

POLL_INTERVAL → Time in seconds between checks (default: 30)

4. Configure printers

Edit printers.json:

[
  {
    "name": "Snapmaker-U1-1",
    "ip": "192.168.1.100",
    "last_status": "idle"
  }
]

You can add multiple printers to the list.

5. Run the notifier
python notifier.py
🐳 Docker Usage
Build
docker build -t snapmaker-notifier .
Run
docker run -d \
  --name snapmaker-notifier \
  --env-file .env \
  -v $(pwd)/printers.json:/app/printers.json \
  snapmaker-notifier
🐳 Docker Compose (Recommended)

Edit .env first, then:

docker-compose up -d
📡 How It Works

The script polls the Moonraker API:

http://<printer-ip>/printer/objects/query?print_stats

It checks:

state

print_duration

filament_used

filename

If the status changes, it sends a Discord embed notification.

🔔 Example Discord Notification

Snapmaker-U1 ▶️ STARTED

State: STARTED

Time: 0h 15m

Filament: 2.3 m

File: test_print.gcode

⚙️ Environment Variables
Variable	Description	Default
DISCORD_WEBHOOK	Discord webhook URL	Required
POLL_INTERVAL	Polling interval in seconds	30
📁 Project Structure
.
├── notifier.py
├── printers.json
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env
🚀 Running as a Background Service (Linux)

Example systemd service:

[Unit]
Description=Snapmaker Discord Notifier
After=network.target

[Service]
WorkingDirectory=/home/user/snapmaker-notifier
ExecStart=/usr/bin/python3 notifier.py
Restart=always
User=user

[Install]
WantedBy=multi-user.target
🛠 Troubleshooting
No Discord messages?

Check webhook URL

Make sure printer IP is correct

Verify Moonraker is running

Test API manually in browser

Printer always offline?

Confirm printer IP

Confirm port (default 80)

Check firewall

📄 License

MIT License

A Thai version

A production-ready README for public release
