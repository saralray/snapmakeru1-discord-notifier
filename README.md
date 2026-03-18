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

    git clone https://github.com/saralray/snapmakeru1-discord-notifier.git
    cd snapmakeru1-discord-notifier

### 2. Create .env file

    DISCORD_TOKEN=
    GUILD_ID=
    CHANNEL_ID=
    POLL_INTERVAL=20

### 3. Run Docker  

    docker compose up -d


------------------------------------------------------------------------


## Run

    python bot.py


