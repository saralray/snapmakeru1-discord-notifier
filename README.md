# Snapmaker U1 Discord Notifier

A lightweight Python service that monitors Snapmaker U1
(Klipper/Moonraker) printers and sends automatic status notifications to
Discord using webhooks.

## Features

-   Detects print started
-   Detects print completed
-   Detects print cancelled
-   Detects idle status
-   Detects offline status
-   Multi-printer support
-   Docker support
-   Configurable polling interval

------------------------------------------------------------------------

## Requirements

-   Python 3.9+
-   Moonraker API enabled
-   Discord Webhook URL

------------------------------------------------------------------------

## Installation

### 1. Clone the repository

    git clone https://github.com/yourusername/snapmakeru1-discord-notifier.git
    cd snapmakeru1-discord-notifier

### 2. Install dependencies

    pip install -r requirements.txt

### 3. Create .env file

    DISCORD_WEBHOOK=https://discord.com/api/webhooks/XXXXXXXX
    POLL_INTERVAL=30

------------------------------------------------------------------------

## Configure printers.json

Example:

\[ { "name": "Snapmaker-U1-1", "ip": "192.168.1.100", "last_status":
"idle" }\]

------------------------------------------------------------------------

## Run

    python notifier.py

------------------------------------------------------------------------

## Docker

Build:

    docker build -t snapmaker-notifier .

Run:

    docker run -d       --name snapmaker-notifier       --env-file .env       -v $(pwd)/printers.json:/app/printers.json       snapmaker-notifier

------------------------------------------------------------------------

## Environment Variables

  Variable          Description               Default
  ----------------- ------------------------- ----------
  DISCORD_WEBHOOK   Discord webhook URL       Required
  POLL_INTERVAL     Poll interval (seconds)   30

------------------------------------------------------------------------

## License

MIT License
