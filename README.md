# Jarvis — Backend

![Tests](https://github.com/Luissoares11/jarvis/actions/workflows/test.yml/badge.svg)

> A modular, self-hosted personal AI assistant built from scratch.

Jarvis is a fully local, API-driven assistant designed to handle real personal productivity needs: memory, reminders, timers, maths, calendar, task boards, weather, and football data. No wrappers around existing assistants. No pre-built frameworks. Every layer written by hand.

---

## Quick Start

### Requirements

- Python 3.12+
- Docker + Docker Compose (for production-style local runs)
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
MEMORY_FILE=data/memory              # defaults to data/memory (→ data/memory.db)
```

### Running locally (Python)

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### Running locally (Docker)

```bash
docker compose build
docker compose up -d
```

The container binds `./data` on the host to `/app/data` inside the container, so the SQLite database and caches persist across rebuilds and restarts.

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
│       ├── notifications.py # GET /notifications
│       └── deploy.py       # POST /deploy — CI-triggered self-deploy (bearer-secret protected)
│
├── cli/
│   └── main.py             # local terminal interface for testing
│
├── tests/
│   └── test_api.py         # integration tests against an isolated test DB
│
├── data/
│   ├── memory.db            # SQLite database (git-ignored, host-mounted volume)
│   ├── memory.json          # legacy/auxiliary memory file (git-ignored)
│   ├── cache/                # cached external API responses (git-ignored)
│   └── plots/                 # generated Plotly HTML files (git-ignored)
│
├── dockerfile
├── docker-compose.yml
├── config.py
└── requirements.txt
```

Each feature under `app/features/` owns its own logic end-to-end — data access, formatting for chat, and (where relevant) a structured-data function consumed directly by its matching router in `server/routers/`. Adding a new feature means adding one file to each folder, not editing a growing central file.

> **Note on `data/`:** `memory.db` and `memory.json` are intentionally git-ignored and were fully untracked from history. They hold live, growing user data and must never be committed — a merge conflict on a tracked binary DB file previously caused real data loss during a deploy. The database lives only on each machine's disk (or the VM's bind-mounted volume) and is not synced via git under any circumstances.

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

The backend runs in Docker on a Proxmox VM (Ubuntu Server 24.04), accessed via Tailscale. Production runs as a Docker Compose service rather than a bare systemd process.

- **Tailscale IP:** `<your-tailscale-ip>`
- **Port:** `8000`
- **Service user:** `jarvisserver`
- **Compose service:** `backend` (container name `jarvis-backend`)
- **Data volume:** `/home/jarvisserver/jarvis/data` → `/app/data` (bind mount — this is what makes the database persist across deploys)

### docker-compose.yml (excerpt)

```yaml
services:
  backend:
    build: .
    container_name: jarvis-backend
    ports:
      - "8000:8000"
    volumes:
      - type: bind
        source: /home/jarvisserver/jarvis/data
        target: /app/data
    env_file: .env
    restart: unless-stopped
```

### Manual deploy (on the VM)

```bash
cd ~/jarvis
git pull
docker compose build
docker compose up -d
```

---

## CI/CD

Every push to `main` runs the full integration test suite via GitHub Actions (`.github/workflows/test.yml`), against an isolated test database — never the production one. If tests pass, a second job deploys automatically:

```
push to main
   │
   ▼
run pytest suite (isolated test DB)
   │  (only if tests pass)
   ▼
join the tailnet (Tailscale GitHub Action, OAuth client)
   │
   ▼
SSH into the VM over Tailscale
   │
   ▼
git pull && docker compose build && docker compose up -d
```

**Tailscale connectivity:** the runner authenticates using a Tailscale OAuth client scoped to `Keys → Auth Keys → Write`, tagged `tag:ci`. The client secret doesn't expire (unlike plain auth keys, capped at 90 days), so no manual rotation is needed.

**Deploy auth:** the SSH key used by the workflow is scoped to a dedicated `deploy`-capable user on the VM, reachable only over the tailnet — never exposed publicly.

**Required GitHub repo secrets:**

| Secret | Purpose |
|---|---|
| `JARVIS_API_TOKEN` | Bearer token used by the test suite |
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID |
| `TS_OAUTH_CLIENT_SECRET` | Tailscale OAuth client secret |
| `VM_HOST` | Tailscale IP/hostname of the deploy VM |
| `VM_USER` | SSH user on the VM |
| `VM_SSH_KEY` | Private key for the deploy user |

---

## Stack

| Layer          | Tech                                        |
|----------------|-----------------------------------------------|
| Language       | Python 3.12                                   |
| API server     | FastAPI + Uvicorn                             |
| Intent parsing | Claude Haiku (Anthropic)                      |
| Memory         | SQLite (WAL mode)                             |
| Maths          | SymPy + Plotly                                |
| Weather        | Open-Meteo (no key needed)                    |
| Football       | football-data.org                             |
| Testing        | pytest + httpx                                |
| CI/CD          | GitHub Actions (test → Tailscale → SSH deploy) |
| Containerization | Docker + Docker Compose                     |
| Networking     | Tailscale (OAuth client, tagged CI node)      |
| Deployment     | Proxmox VM + Docker Compose + Tailscale       |

---

*Built by Luís Soares*