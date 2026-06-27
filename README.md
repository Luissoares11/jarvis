# Jarvis — Backend

![Tests](https://github.com/Luissoares11/jarvis/actions/workflows/test.yml/badge.svg)

> A modular, self-hosted personal AI assistant built from scratch.

Jarvis is a fully local, API-driven assistant designed to handle real personal productivity needs: memory, reminders, timers, maths, calendar, task boards, weather, and football data. No wrappers around existing assistants. No pre-built frameworks. Every layer written by hand.

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

### Running tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
jarvis/
├── app/
│   ├── core.py             # handler registry + process_input entry point
│   ├── llm.py              # intent parsing via Claude Haiku + pattern cache
│   ├── parser.py           # raw input pre-processing / pattern matching
│   ├── personality.py      # response templates for social/greeting inputs
│   ├── reasoning.py        # conflict detection + inference
│   ├── relations.py        # fact relation definitions
│   ├── utils.py
│   ├── logger.py
│   ├── commands.py         # local debug commands (jarvis facts, jarvis history, ...)
│   │
│   ├── actions/            # todos, reminders, timers — chat-driven actions
│   │
│   ├── compute/            # symbolic maths (SymPy) + plotting (Plotly)
│   │
│   ├── features/           # one module per feature — REST + chat logic
│   │   ├── cache.py        # shared file-cache helper
│   │   ├── weather.py      # Open-Meteo lookup + structured data for REST
│   │   ├── football.py     # fixtures, results, standings (football-data.org)
│   │   ├── calendar.py     # calendar events — CRUD + chat formatting
│   │   └── tasks.py        # task boards — CRUD + chat formatting
│   │
│   └── memory/
│       ├── api.py          # high-level memory operations
│       ├── store.py        # SQLite layer + DB init
│       ├── context.py      # per-session context factory
│       ├── resolver.py     # entity + pronoun resolution
│       └── models.py
│
├── server/
│   ├── main.py             # FastAPI app, lifespan, middleware
│   ├── auth.py             # bearer token verification
│   ├── sessions.py         # per-session context store
│   └── routers/            # one router per feature, included into main.py
│       ├── chat.py         # POST /chat — LLM intent pipeline
│       ├── tasks.py        # GET /tasks, /boards, /boards/:id/tasks
│       ├── calendar.py     # GET /events
│       ├── weather.py      # GET /weather
│       ├── timers.py       # GET /timers
│       └── notifications.py # GET /notifications
│
├── cli/
│   └── main.py             # local terminal interface for testing
│
├── tests/
│   └── test_api.py         # integration tests against an isolated test DB
│
├── data/
│   ├── memory.db           # SQLite database (git-ignored)
│   ├── cache/               # cached external API responses (git-ignored)
│   └── plots/               # generated Plotly HTML files (git-ignored)
│
├── config.py
└── requirements.txt
```

Each feature under `app/features/` owns its own logic end-to-end — data access, formatting for chat, and (where relevant) a structured-data function consumed directly by its matching router in `server/routers/`. Adding a new feature means adding one file to each folder, not editing a growing central file.

---

## Architecture

```
user input
    │
    ▼
 hardcoded check          ← greetings, social (free, no API call)
    │
    ▼
 pattern cache lookup     ← exact + fuzzy match on confirmed patterns
    │
    ▼
 LLM intent parser        ← Claude Haiku returns structured action JSON
    │
    ▼
 handler registry (core.py) ← dispatches to the right feature/action module
    │
    ▼
 memory / compute / features / actions
```

REST clients (the desktop UI, future phone app) bypass the LLM pipeline entirely for read operations — `server/routers/*` query the database or feature modules directly and return JSON, no string parsing required on the frontend.

Context is passed explicitly through the call chain — no global state, safe for concurrent sessions.

---

## Deployment

The backend runs on a Proxmox VM (Ubuntu Server 24.04), accessed remotely via Tailscale.

- **Tailscale IP:** `<your-tailscale-ip>`
- **Port:** `8000`
- **Service user:** `jarvisserver`
- **Service file:** `/etc/systemd/system/jarvis.service`

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

### CI

Every push to `main` runs the full integration test suite via GitHub Actions (`.github/workflows/test.yml`), against an isolated test database — never the production one.

---

## Stack

| Layer          | Tech                              |
|----------------|------------------------------------|
| Language       | Python 3.12                       |
| API server     | FastAPI + Uvicorn                 |
| Intent parsing | Claude Haiku (Anthropic)          |
| Memory         | SQLite (WAL mode)                 |
| Maths          | SymPy + Plotly                    |
| Weather        | Open-Meteo (no key needed)        |
| Football       | football-data.org                 |
| Testing        | pytest + httpx                    |
| CI             | GitHub Actions                    |
| Deployment     | Proxmox VM + systemd + Tailscale  |

---


*Built by Luís Soares*