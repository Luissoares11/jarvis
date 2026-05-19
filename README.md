# Jarvis

> A modular, self-hosted personal AI assistant — built from scratch.

Jarvis is a fully local, API-driven assistant I built to handle the things I actually need: memory, reminders, maths, football scores, weather, and a calendar that syncs to Google. No wrappers around existing assistants. No pre-built frameworks. Every layer written by hand.

---

## What it does

**Memory** — Jarvis remembers facts about people and things across sessions. Ask it about someone and it'll pull from a structured SQLite store, resolve pronouns, follow relationship chains, and detect conflicts when you try to update something it already knows.

**Natural language understanding** — Input goes straight to Claude Haiku for intent parsing. No regex pipelines, no hand-written grammars. The parsed action is cached locally so repeated phrases are free and instant. Typos, rephrasing, different word order — it handles it.

**Computation** — Symbolic maths via SymPy. Derivatives, integrals, limits, equation solving, unit conversions, and function plotting.

**External data** — Live weather via Open-Meteo (no API key needed). Football fixtures, results, and standings via football-data.org. All responses are cached to avoid burning API calls.

**Actions** — To-do lists, reminders with real timers, countdown timers, alarms, and calendar events with Google Calendar sync.

**API** — FastAPI server with bearer token auth and per-session context. Designed to be called from a phone UI (in progress).

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
 handler registry         ← dispatches to the right module
    │
    ▼
 memory / compute /       ← SQLite, SymPy, httpx, Google Calendar
 external / actions
```

Context is passed explicitly through the call chain — no global state, safe for concurrent sessions.

---

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.12 |
| API server | FastAPI + Uvicorn |
| Intent parsing | Claude Haiku (Anthropic) |
| Memory | SQLite (WAL mode, indexed) |
| Maths | SymPy + Matplotlib |
| Weather | Open-Meteo |
| Football | football-data.org |
| Calendar | Google Calendar API |
| Deployment | Proxmox VM + systemd + Tailscale |

---

## Project structure

```
jarvis/
├── app/
│   ├── core.py          # handler registry + process_input
│   ├── llm.py           # intent parsing + pattern cache
│   ├── actions.py       # todos, reminders, timers, calendar
│   ├── compute.py       # symbolic maths + plotting
│   ├── external.py      # weather + football
│   ├── personality.py   # response templates
│   ├── reasoning.py     # conflict detection + inference
│   ├── relations.py     # fact relation definitions
│   └── memory/
│       ├── api.py       # high-level memory operations
│       ├── store.py     # SQLite layer
│       ├── context.py   # per-session context
│       └── resolver.py  # entity + pronoun resolution
├── cli/
│   └── main.py          # local terminal interface
├── main.py              # FastAPI entrypoint
├── config.py
└── requirements.txt
```

## Roadmap

- [x] Core memory system — facts, collections, aliases
- [x] Intelligence layers — conflict detection, pronoun resolution, inference
- [x] Computation engine — SymPy + plotting
- [x] External data — weather, football
- [x] Actions — todos, reminders, timers, Google Calendar
- [x] API server — FastAPI, auth, session context
- [ ] Server deployment — Proxmox VM, systemd, Tailscale
- [ ] Phone UI — mobile chat interface
- [ ] Voice — Whisper STT, local TTS, wake word
- [ ] Device control — smart home, scripts, automations
- [ ] Advanced reasoning — multi-step planning, proactive suggestions

---

*Built by Luís Soares*