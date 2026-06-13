# Jarvis Backend — Architecture

## Overview

The backend is a FastAPI server that receives natural language input, parses intent using an LLM, dispatches to the right handler, and returns a formatted response. It is stateless between requests except for per-session context passed explicitly through the call chain.

---

## Request Pipeline

```
user input (POST /chat)
    │
    ▼
[1] hardcoded check
    └── greetings, social phrases → immediate response, no API call
    │
    ▼
[2] pattern cache lookup
    └── SQLite table of confirmed input → action mappings
    └── exact match first, then fuzzy match
    └── cache hit → skip LLM entirely
    │
    ▼
[3] LLM intent parser (Claude Haiku)
    └── input + session context → structured action JSON
    └── example: { "action": "action_add_todo", "task": "buy milk" }
    └── confirmed response is written back to pattern cache
    │
    ▼
[4] handler registry (core.py)
    └── dispatches action string to the correct module function
    │
    ▼
[5] handler execution
    └── memory / compute / external / actions
    │
    ▼
[6] response string → back to client
```

### Why LLM-first?

Previous versions used a regex/normalization pipeline for intent parsing. It was brittle — any new phrasing required manual rules, typos broke it, and the codebase grew unmaintainable. Replacing it with Claude Haiku for intent parsing and a local SQLite cache for repeated phrases solved all of these problems. The LLM is only called when genuinely needed; cached patterns make repeated commands free and instant.

---

## Session Context

Each request includes a `session_id`. The server maintains a dict of session contexts in memory:

```python
_sessions: dict[str, dict] = {}
```

Context is created by `make_context()` and passed explicitly through the entire call chain — no global state, safe for concurrent sessions. This means different clients (desktop UI, mini mode, phone UI) can maintain separate conversation histories using different session IDs.

Current session IDs in use:
- `"desktop"` — main chat window
- `"panels"` — panel data fetches (weather, tasks, events, reminders)
- `"mini"` — mini mode input bar
- `"health"` — ping checks

---

## Data Layer

All persistent data is stored in a single SQLite database at `data/jarvis.db`, initialized by `app/memory/store.py` on startup.

### Tables

**`todos`**
```sql
id TEXT PRIMARY KEY,
task TEXT,
priority TEXT DEFAULT 'normal',
done INTEGER DEFAULT 0,
created_at TEXT
```

**`reminders`**
```sql
id TEXT PRIMARY KEY,
message TEXT,
remind_at TEXT,
fired INTEGER DEFAULT 0,
created_at TEXT
```

**`events`**
```sql
id TEXT PRIMARY KEY,
title TEXT,           -- stored with emoji prefix: "📅 Event: Title"
start_time TEXT,      -- ISO datetime with timezone
end_time TEXT,
notes TEXT,
created_at TEXT
```

**`notifications`**
```sql
id TEXT PRIMARY KEY,
message TEXT,
read INTEGER DEFAULT 0,
created_at TEXT
```

**`memory` / `facts` / `entities`** — see `app/memory/store.py` for full schema.

### Known issue — event title storage

Event titles are stored with their type emoji prefix (e.g. `"📅 Event: Fases Finais - Valorant"`). This was an early design decision that now requires the frontend to strip the prefix when displaying. Future refactor: store `title` and `type` as separate columns, format on output only.

---

## Modules

### `app/core.py`
Entry point for all input processing. Calls the pipeline in order (hardcoded → cache → LLM → handler). Returns a string response.

### `app/llm.py`
Wraps Claude Haiku for intent parsing. Returns a structured dict like:
```json
{ "action": "action_add_todo", "task": "buy milk", "priority": "high" }
```
Also manages the pattern cache — reads before calling the LLM, writes after a successful parse.

### `app/actions.py`
Handles all user-facing actions:
- **Todos** — `add_todo`, `list_todos`, `complete_todo`, `delete_todo`
- **Reminders** — `add_reminder`, `list_reminders`, `load_pending_reminders`
- **Timers** — `set_timer` (in-memory threading.Timer + end time tracking)
- **Calendar** — `add_event`, `list_events`, `delete_event`, `edit_event`
- **Alarm** — alias for `add_reminder`

**Timer architecture:** Timers are stored in `_timer_threads` as:
```python
{ timer_id: { "timer": Timer, "label": str, "ends_at": ISO_string } }
```
The `ends_at` field enables the `/timers` endpoint to return remaining time without needing the thread itself.

### `app/compute.py`
Symbolic computation via SymPy. Handles derivatives, integrals, limits, equation solving, unit conversions. Plotting via Plotly — saves HTML to `data/plots/` and returns a `PLOT:filename` token the frontend uses to open the file.

### `app/external.py`
- **Weather:** Open-Meteo API, no key required, geocoding by city name
- **Football:** football-data.org, fixtures + standings + results

### `app/memory/`
Full memory system — facts about people and things, entity resolution, pronoun resolution, relationship chains, conflict detection. All backed by SQLite.

---

## API Reference

### Authentication
All endpoints (except `/health`) require a Bearer token:
```
Authorization: Bearer <JARVIS_API_TOKEN>
```

### Endpoints

#### `POST /chat`
Main entry point for all natural language input.

**Request:**
```json
{
  "message": "set a timer for 10 minutes",
  "session_id": "desktop"
}
```

**Response:**
```json
{
  "response": "Timer set for 10m: 'Timer'.",
  "session_id": "desktop"
}
```

#### `GET /health`
Returns `{"status": "ok"}`. Used by the UI for connection checks.

#### `GET /timers`
Returns all active countdown timers with remaining time.

**Response:**
```json
{
  "timers": [
    {
      "id": "uuid",
      "label": "pasta",
      "ends_at": "2026-06-01T01:56:02+01:00",
      "remaining_seconds": 342
    }
  ]
}
```

#### `GET /notifications`
Returns unread notifications and marks them as read.

**Response:**
```json
{
  "notifications": [
    { "id": "uuid", "message": "Take the pasta out" }
  ]
}
```

#### `GET /plots/<filename>`
Serves generated Plotly HTML files as static files.

---

## Known Technical Debt

- **Debug logging** — `[DEBUG]` and `[LLM RAW]` print statements throughout `app/llm.py` and `app/core.py`. Remove before any public distribution.
- **String-formatted responses** — `list_events`, `list_todos`, `list_reminders` return formatted strings instead of structured JSON. The frontend has to parse these with regex. Priority refactor: add `GET /events`, `GET /tasks`, `GET /reminders` endpoints that return proper JSON arrays.
- **Event title prefix** — emoji type prefix stored in the title column. Should be separated into a `type` column.
- **Timer persistence** — timers are in-memory only. A server restart clears all active timers. Reminders survive restarts (re-armed from DB on startup via `load_pending_reminders`), timers do not.
- **No pagination** — `list_events(all_events=True)` returns everything. Will need limits as data grows.

---

## Roadmap

### Immediate
- [ ] Strip debug logging
- [ ] Add `GET /events`, `GET /tasks`, `GET /reminders` JSON endpoints
- [ ] Separate event `title` and `type` in DB schema

### Stage 10 — Phone/Tablet UI
- [ ] React Native app connecting to same backend over Tailscale
- [ ] Notes system — new `notes` table + CRUD endpoints + UI

### Stage 11 — Voice
- [ ] Whisper STT for speech input
- [ ] Local TTS for spoken responses
- [ ] Wake word detection ("Hey Jarvis")

### Stage 12 — Device Control
- [ ] Smart home integrations
- [ ] Script execution
- [ ] Automations

### Stage 13 — Advanced Reasoning
- [ ] Multi-step planning
- [ ] Proactive suggestions based on calendar/reminders
