# Jarvis — Backend

![Tests](https://github.com/Luissoares11/jarvis/actions/workflows/test.yml/badge.svg)

> A modular, self-hosted personal AI assistant built from scratch.

Jarvis is a fully local, API-driven assistant designed to handle real personal productivity needs: memory, reminders, timers, maths, calendar, weather, and football data. No wrappers around existing assistants. No pre-built frameworks. Every layer written by hand.

---

## Quick Start

### Requirements

- Python 3.12+
- Anthropic API key (for Claude Haiku intent parsing)
- Optional: football-data.org API key

### Setup

```bash
git clone https://github.com/Luissoares11/jarvis
cd jarvis
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
```

### Environment variables

```env
ANTHROPIC_API_KEY=your_key_here
JARVIS_API_TOKEN=your_bearer_token
FOOTBALL_API_KEY=your_key_here       # optional
TIMEZONE=Europe/Lisbon
```

### Running locally

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### Running via systemd (production)

```bash
sudo systemctl start jarvis
sudo systemctl status jarvis
journalctl -u jarvis -f
```

---

## Project Structure

```
jarvis/
├── app/
│   ├── core.py           # handler registry + process_input entry point
│   ├── llm.py            # intent parsing via Claude Haiku + pattern cache
│   ├── actions.py        # todos, reminders, timers, calendar events
│   ├── compute.py        # symbolic maths (SymPy) + plotting (Plotly)
│   ├── external.py       # weather (Open-Meteo) + football (football-data.org)
│   ├── personality.py    # response templates for social/greeting inputs
│   ├── reasoning.py      # conflict detection + inference
│   ├── relations.py      # fact relation definitions
│   └── memory/
│       ├── api.py        # high-level memory operations
│       ├── store.py      # SQLite layer + DB init
│       ├── context.py    # per-session context factory
│       └── resolver.py   # entity + pronoun resolution
├── server/
│   └── main.py           # FastAPI app, routes, auth, lifespan
├── cli/
│   └── main.py           # local terminal interface for testing
├── data/
│   ├── jarvis.db         # SQLite database (git-ignored)
│   └── plots/            # generated Plotly HTML files
├── config.py
└── requirements.txt
```

---

## Deployment

The backend runs on a Proxmox VM (Ubuntu Server 24.04), accessed remotely via Tailscale.

- **Tailscale IP:** `<your-tailscale-ip>`
- **Port:** `8000`
- **Service user:** `your-user`
- **Service file:** `your-file-path`

### systemd service

```ini
[Unit]
Description=Jarvis AI Assistant
After=network.target

[Service]
Type=simple
User=jarvisserver
WorkingDirectory=/home/jarvisserver/jarvis
ExecStart=/usr/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/jarvisserver/jarvis/.env

[Install]
WantedBy=multi-user.target
```

---

## Stack

| Layer          | Tech                          |
|----------------|-------------------------------|
| Language       | Python 3.12                   |
| API server     | FastAPI + Uvicorn             |
| Intent parsing | Claude Haiku (Anthropic)      |
| Memory         | SQLite (WAL mode)             |
| Maths          | SymPy + Plotly                |
| Weather        | Open-Meteo (no key needed)    |
| Football       | football-data.org             |
| Deployment     | Proxmox VM + systemd + Tailscale |
