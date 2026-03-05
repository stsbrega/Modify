# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ModdersOmni is an AI-powered game modding assistant. Users input their PC hardware specs and gameplay preferences, then an LLM generates a personalized mod list by searching Nexus Mods in real time. Currently supports Skyrim SE/AE and Fallout 4.

## Tech Stack

- **Frontend**: Angular 19.2 (standalone components, no NgModules) + Tailwind CSS 4 + inline SCSS
- **Backend**: Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 (async) + Pydantic 2
- **Database**: PostgreSQL 16 (asyncpg)
- **Auth**: JWT (python-jose) + bcrypt (direct, not passlib — passlib is incompatible with bcrypt 4+/Python 3.13+) + OAuth (authlib — Google, Discord) + email verification (fastapi-mail)
- **LLM**: OpenAI-compatible SDK supporting 7 providers (Anthropic, OpenAI, Gemini, Groq, Together AI, DeepSeek, Mistral)
- **Mod API**: Nexus Mods v2 GraphQL API (per-user API keys)
- **Deployment**: Render (Python backend, static frontend, managed PostgreSQL). Defined in `render.yaml`.

## Common Commands

### Backend (run from `backend/`)

```bash
pip install -r requirements.txt          # Install deps
uvicorn app.main:app --reload            # Dev server (localhost:8000)
python -m app.seeds.run_seed             # Create tables + seed data
ruff check app/                          # Lint (hard-fail in CI)
mypy app/ --ignore-missing-imports --no-strict-optional  # Type check
pytest tests/ -v                         # Tests (require PostgreSQL or aiosqlite)
```

### Local Dev Environment
- Local Python is 3.14; `requirements.txt` pins versions for Render (Python 3.12). Install deps individually (`pip install <pkg>`) if pinned versions fail to build.
- Running tests requires `aiosqlite` (not in requirements.txt): `pip install aiosqlite`
- `conftest.py` imports `app.main` which chains all app imports — all backend deps must be installed even for pure unit tests

### Frontend (run from `frontend/`)

```bash
npm install                              # Install deps
npm start                                # Dev server (localhost:4200, proxies /api to :8000)
npx ng build --configuration=production  # Production build (hard-fail in CI)
npm test                                 # Karma/Jasmine tests
```

### CI (GitHub Actions — `.github/workflows/ci.yml`)

Runs on push/PR to main:
- Backend: `ruff check` (hard-fail), `mypy` (soft), `pytest` (hard-fail, graceful if no tests)
- Frontend: `ng build --configuration=production` (hard-fail), `ng lint` (soft)

PostgreSQL service container used for backend tests. Health check: `pg_isready -U modify -d modify_test`.

## Architecture

### Generation Pipeline (Core Feature)

The generation system is the heart of the app — an LLM searches Nexus Mods in real time and builds a modlist phase by phase.

**Flow**: `POST /api/generation/start` → background task → SSE streaming → `GET /api/generation/{id}/events`

**Key files**:
- `backend/app/api/generation.py` — HTTP endpoints (start, events SSE, status polling, resume)
- `backend/app/services/generation_manager.py` — In-memory singleton tracking all active generations (events, subscribers, status)
- `backend/app/services/modlist_generator.py` — Core generation logic (1000+ lines): phased tool-calling loop

**Phased architecture**: Each game has ordered `ModBuildPhase` records in the DB (e.g., Skyrim has ~10 phases: Essentials → UI → Textures → Gameplay → Combat → Environment → ... → Compatibility Patches). The LLM processes one phase at a time.

**Tool-calling loop**: The LLM has tools: `search_nexus`, `get_mod_details`, `add_to_modlist`, `finalize`. For the final patch-review phase: `search_patches`, `add_patch`, `flag_user_knowledge`, `finalize_review`. The loop runs until the LLM calls `finalize`.

**SSE streaming**: Events are emitted via `GenerationManager.emit()` → stored in list + pushed to subscriber queues. Frontend subscribes via `EventSource`. Events replay on reconnect (reconnection-safe). Event types: `phase_start`, `phase_complete`, `thinking`, `searching`, `mod_added`, `provider_error`, `provider_switch`, `paused`, `complete`, `error`.

**Multi-provider fallback**: If provider A fails on a phase, tries provider B from user's configured keys. If all fail, emits `paused` event. `GenerationSession` dataclass captures full state (modlist, patches, knowledge flags, completed phases, description cache) for resume.

**Pause/resume**: `PauseGeneration` exception carries `session_snapshot`. Frontend can `POST /api/generation/{id}/resume` to restart from the paused phase with potentially different API keys.

### LLM Provider System

**Files**: `backend/app/llm/provider.py` (abstract base + OpenAI-compatible impl), `backend/app/llm/registry.py` (provider catalog)

Registry pattern — 7 providers with id, name, model, base_url, requires_key. Factory: `LLMProviderFactory.create_from_request(provider_id, api_key, base_url, model)`. All use OpenAI-compatible API format.

Key methods: `generate(system_prompt, user_prompt)` for simple completions, `generate_with_tools(messages, tools, tool_handlers, max_iterations)` for the tool-calling loop used in generation.

### Nexus Mods Integration

**File**: `backend/app/services/nexus_client.py` — GraphQL client for Nexus Mods v2 API.

- Semaphore: max 10 concurrent requests
- Retry: exponential backoff (rate limits: 5s/10s/20s; server errors: 3s/6s/12s)
- Per-user API keys (no server-side fallback) — user must provide their own key in Settings

### Frontend Architecture

Angular 19 standalone components with feature-based organization. Key routing:

| Route | Component | Auth |
|-------|-----------|------|
| `/setup` | Hardware detection + playstyle + Nexus key + AI provider config | Optional (redirects to register on generate) |
| `/generate/:id` | Real-time SSE streaming UI | Required |
| `/modlist/:id` | View generated modlist | Public |
| `/downloads` | Download progress (WebSocket) | Required |
| `/dashboard` | User's saved modlists | Required |
| `/settings` | LLM provider & API key management | Required |

**Generation streaming**: `core/services/generation.service.ts` wraps `EventSource` for SSE. The generation component (`features/generation/`) renders events in real time with animations.

**Setup wizard**: `features/setup/steps/playstyle-select/` contains the main wizard step with game selection, playstyle choice, Nexus API key input, and AI provider key configuration. Keys are saved to user profile via `PUT /api/settings/`. Generation is gated on both Nexus key and at least one LLM provider key.

**API base URL**: Reads `window.__env.API_URL` (generated at build time on Render) with fallback to `/api` (proxied to localhost:8000 in dev via `proxy.conf.json`).

## Project Structure

```
backend/
  app/
    api/              # FastAPI route handlers
      auth.py         #   /auth/* — register, login, OAuth, email verify, password reset
      generation.py   #   /generation/* — start, SSE events, status, resume
      modlist.py      #   /modlist/* — retrieve modlists
      downloads.py    #   /downloads/* — start downloads, status, WebSocket progress
      settings.py     #   /settings/ — user settings (Nexus key, LLM keys)
      games.py        #   /games/ — game list, playstyles
      specs.py        #   /specs/parse — hardware text parsing
      stats.py        #   /stats/ — landing page metrics
      deps.py         #   JWT dependency injection (get_current_user eagerly loads User.settings)
    models/           # SQLAlchemy ORM (User, Modlist, ModlistEntry, ModBuildPhase, Game, Playstyle, etc.)
    schemas/          # Pydantic request/response schemas
    services/         # Business logic
      modlist_generator.py  # Core: phased LLM tool-calling generation
      generation_manager.py # In-memory generation state + SSE event dispatch
      nexus_client.py       # Nexus Mods v2 GraphQL client
      auth.py               # JWT creation/validation, password hashing
      email.py              # SMTP email sending
      oauth.py              # OAuth provider abstraction (Google, Discord)
      spec_parser.py        # Hardware text parsing (regex-based)
      tier_classifier.py    # GPU/CPU tier classification (low/mid/high/ultra)
      download_manager.py   # Async mod download orchestration
    llm/              # LLM provider abstraction
      provider.py     #   Abstract base + OpenAI-compatible implementation
      registry.py     #   Provider catalog (7 providers)
    seeds/            # Database seed data (run_seed.py creates tables + seeds games/playstyles/phases)
    config.py         # Settings via pydantic-settings (.env)
    database.py       # SQLAlchemy async engine + session factory
    main.py           # FastAPI app entry + lifespan (DB init, seed, CORS)
  tests/              # pytest + pytest-asyncio
  alembic/            # Migration config (not actively used — seed uses create_all)

frontend/
  src/app/
    core/
      services/       # ApiService, AuthService, GenerationService, NotificationService, ThemeService
      interceptors/   # AuthInterceptor (JWT header), ErrorInterceptor
      guards/         # authGuard, guestGuard
    shared/
      components/     # header, notification-toast
      models/         # TypeScript interfaces
    features/
      auth/           # Login, register, OAuth callback, email verify, password reset
      setup/          # Hardware setup wizard (game-select, spec-input, playstyle-select)
      generation/     # Real-time SSE streaming UI during modlist generation
      modlist/        # Generated mod list view
      downloads/      # Download progress view (WebSocket)
      dashboard/      # User's saved modlists
      settings/       # User settings
      browse/         # Mod browsing
      landing/        # Landing page
    app.routes.ts     # Top-level routing
    app.config.ts     # App config (providers, interceptors)
  proxy.conf.json     # Dev proxy: /api → localhost:8000
  public/env-config.js # Runtime API URL (generated on Render)
```

## Code Conventions

### Backend
- Async throughout (`async def`, `await`)
- Models in `models/`, Pydantic schemas in `schemas/`, business logic in `services/`
- All API routes prefixed with `/api/`
- `ruff` for linting, `black` for formatting
- `get_current_user` dependency (in `deps.py`) eagerly loads `User.settings` via `selectinload` — no extra DB query needed in endpoints

### Frontend
- Angular 19 standalone component API (no NgModules)
- Feature components use **inline templates and styles** (single `.ts` files)
- CSS custom properties defined in `styles.scss` for theming; component styles use inline SCSS
- Fonts: DM Sans (body) + Playfair Display (headings) via Google Fonts — use simple weight syntax (`wght@300;400;500;600;700`), NOT variable font axis syntax (causes 400 errors during Angular font inlining)

## Deployment (Render)

- **Frontend**: `https://moddersomni-web.onrender.com` (static site)
- **Backend**: `https://moddersomni-api.onrender.com/api` (Python 3.12 native runtime)
- **Database**: Managed PostgreSQL 16

Infrastructure defined in `render.yaml`. Push to `main` auto-deploys. Pre-deploy runs `python -m app.seeds.run_seed`.

Env vars marked `sync: false` in `render.yaml` must be set manually in Render dashboard: OAuth credentials (Google, Discord), SMTP credentials, `GROQ_API_KEY`.

Ollama (local LLM) does not work on Render — use cloud providers.

## Content Filtering Note

When generating code or text related to custom mod sources, use generic terms like "custom mod source" rather than naming specific adult content sites. The Anthropic API blocks responses containing explicit site references.
