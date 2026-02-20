# CLAUDE.md

## Project Overview

ModdersOmni is an AI-powered game modding assistant that generates personalized mod lists based on hardware specs and gameplay preferences. It targets Skyrim SE/AE and Fallout 4.

## Tech Stack

- **Frontend**: Angular 19.2 (standalone components) + Tailwind CSS 4 + CSS custom properties + inline SCSS + TypeScript 5.7
- **Backend**: Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2
- **Database**: PostgreSQL 16 (via asyncpg)
- **Auth**: JWT (python-jose) + bcrypt (passlib) + OAuth (authlib) + email verification (fastapi-mail)
- **Migrations**: Alembic (no migrations yet — seed script uses `create_all`)
- **LLM**: OpenAI-compatible client (`openai` SDK) — supports Ollama (local), Groq, Together AI, HuggingFace (cloud)
- **Mod API**: Nexus Mods v2 GraphQL API + optional custom mod source
- **Deployment**: Render (production) — Python native runtime (backend), static site (frontend), managed PostgreSQL. Defined in `render.yaml` blueprint.
- **License**: GPL-3.0

## Project Structure

```
backend/
  app/
    api/              # FastAPI route handlers
      auth.py         #   /auth/* — register, login, OAuth, email verify, password reset, change password
      deps.py         #   JWT dependency injection (get_current_user, get_current_user_optional, require_verified_email)
      games.py        #   GET /games/, GET /games/{game_id}/playstyles
      specs.py        #   POST /specs/parse
      modlist.py      #   POST /modlist/generate, GET /modlist/{modlist_id}, GET /modlist/mine
      downloads.py    #   POST /downloads/start, GET /downloads/{id}/status, WS /downloads/{id}/ws
      settings.py     #   GET /settings/, PUT /settings/ (requires auth)
      stats.py        #   GET /stats/ — landing page metrics
    models/           # SQLAlchemy ORM models
      user.py         #   User (auth, profile, hardware specs)
      user_settings.py#   UserSettings (per-user preferences)
      refresh_token.py#   RefreshToken (JWT rotation)
      email_verification.py # EmailVerification
      game.py         #   Game
      playstyle.py    #   Playstyle
      mod.py          #   Mod
      modlist.py      #   ModList
      compatibility.py#   CompatibilityRule
      playstyle_mod.py#   PlaystyleMod (junction table)
    schemas/          # Pydantic request/response schemas (auth, game, modlist, specs, stats)
    services/         # Business logic
      auth.py         #   JWT creation/validation, password hashing, token management
      email.py        #   SMTP email sending (verification, password reset)
      oauth.py        #   OAuth provider abstraction (Google, Discord)
      spec_parser.py  #   Hardware text parsing (regex-based)
      tier_classifier.py # GPU/CPU tier classification (low/mid/high/ultra)
      modlist_generator.py # LLM-powered mod list generation (with DB fallback)
      nexus_client.py #   Nexus Mods v2 GraphQL client
      custom_source_client.py # Generic custom mod source API client
      download_manager.py # Async mod download orchestration
    llm/              # LLM provider abstraction (OpenAI-compatible)
    seeds/            # Database seed data (run_seed.py, seed_data.py)
    config.py         # Settings via pydantic-settings
    database.py       # SQLAlchemy async engine setup
    main.py           # FastAPI app entry point
  alembic/            # Migration config (no versions/ dir yet — seed uses create_all)
  tests/              # pytest + pytest-asyncio (file-based SQLite via aiosqlite)
  .env.example        # Environment variable reference

frontend/
  src/app/
    core/
      services/       # ApiService, AuthService, NotificationService, ThemeService
      interceptors/   # AuthInterceptor, ErrorInterceptor
      guards/         # authGuard, guestGuard (both in auth.guard.ts)
    shared/
      components/     # header, notification-toast
      models/         # TypeScript interfaces (auth, game, mod, specs)
    features/
      auth/           # Login, register, OAuth callback, email verify, password reset
      browse/         # Mod browsing view
      dashboard/      # Main dashboard view
      landing/        # Landing page
      setup/          # Hardware setup wizard
        steps/        #   game-select, playstyle-select, spec-input sub-components
      modlist/        # Generated mod list view
      downloads/      # Download progress view
      settings/       # User settings view
    app.routes.ts     # Top-level routing
    app.config.ts     # App config (providers, authInterceptor, errorInterceptor)
  public/env-config.js # Runtime API URL config (generated at build time on Render)
```

## Common Commands

### Quick Start (first time)

```bash
# 1. Backend setup (from backend/)
cp .env.example .env                     # Configure env vars (defaults work for local dev)
pip install -r requirements.txt
# Ensure PostgreSQL is running locally
python -m app.seeds.run_seed             # Creates tables + seeds data
uvicorn app.main:app --reload            # Backend on localhost:8000

# 2. Frontend setup (from frontend/)
npm install
npm start                                # Frontend on localhost:4200 (proxies /api to localhost:8000)
```

### Backend (run from `backend/`)

```bash
pip install -r requirements.txt        # Install dependencies
uvicorn app.main:app --reload           # Dev server (localhost:8000)
pytest tests/ -v                        # Run tests
# Note: tests require aiosqlite (pip install aiosqlite) — not yet in requirements.txt
ruff check app/                         # Lint
black app/                              # Format
mypy app/ --ignore-missing-imports --no-strict-optional  # Type check
alembic upgrade head                    # Run migrations
python -m app.seeds.run_seed            # Seed database (also creates tables via create_all)
```

### Frontend (run from `frontend/`)

```bash
npm install                             # Install dependencies
npm start                               # Dev server (localhost:4200)
npm run build                           # Production build
npm test                                # Run Karma/Jasmine tests
```

### Deployment (Render)

#### Production URLs
- **Frontend**: `https://moddersomni-web.onrender.com`
- **Backend API**: `https://moddersomni-api.onrender.com/api`
- **OAuth callbacks**: `https://moddersomni-api.onrender.com/api/auth/oauth/{provider}/callback`

Infrastructure is defined in `render.yaml` (Blueprint). Push to GitHub and deploy via Render dashboard → Blueprints → New Blueprint Instance.

- **Backend**: Python 3.12 native runtime. Render provides `PORT` env var. Start command transforms Render's `postgres://` URL to `postgresql+asyncpg://` format.
- **Frontend**: Static site. Build command generates `public/env-config.js` with `API_URL` before Angular build. SPA routing handled by Render rewrite rules.
- **Database**: Render managed PostgreSQL 16. Pre-deploy command runs `python -m app.seeds.run_seed`.
- **Env vars marked `sync: false`** must be set manually in Render dashboard after first deploy: `GROQ_API_KEY`, `NEXUS_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SMTP_USER`, `SMTP_PASSWORD`. All other env vars (URLs, redirect URIs, SMTP host) are hardcoded in `render.yaml` and auto-fill on deploy.

**Note**: Ollama (local LLM) does not work on Render — use a cloud provider (Groq, Together AI, etc.).

**Note**: Google Fonts CSS2 API — use simple weight syntax (`DM+Sans:wght@300;400;500;600;700`), not variable font axis syntax (`ital,opsz,wght@...`) which returns 400 errors during Angular font inlining.

## Code Conventions

### Backend
- Follow PEP 8; use `black` for formatting and `ruff` for linting
- Async endpoints throughout (async def, await)
- Models in `models/`, Pydantic schemas in `schemas/`, business logic in `services/`
- API routes prefixed with `/api/`
- Environment config via `.env` file (see `backend/.env.example`)
- Key env vars (have local-dev defaults in `config.py`): `DATABASE_URL`, `SECRET_KEY`. Optional groups: LLM provider (Ollama default, no key needed), Nexus API, SMTP email, OAuth (Google/Discord), custom mod source
- Settings are per-user in the `user_settings` PostgreSQL table (requires authentication)
- LLM modlist generation falls back to curated DB mods if LLM call fails

### Frontend
- Angular 19 standalone component API (no NgModules)
- Feature components use inline templates/styles (single `.ts` files)
- Feature-based folder organization under `features/`
- Shared reusable components under `shared/components/`
- Core singleton services under `core/services/`
- CSS custom properties (design tokens in `styles.scss`) for theming; inline SCSS for component styles
- Fonts: DM Sans (body) + Playfair Display (headings) loaded via Google Fonts in `index.html`
- Models defined as TypeScript interfaces in `shared/models/`
- API base URL: reads `window.__env.API_URL` (set at build time on Render, or via `public/env-config.js` locally) with fallback to `/api` (proxied to localhost:8000 in dev via `proxy.conf.json`)
- Route auth: browse, setup, downloads are public; dashboard and settings require `authGuard`; modlist generation checks auth in `playstyle-select` component and redirects to register

## API Endpoints

- `GET  /api/health` — Health check
- `GET  /api/stats/` — Landing page statistics (modlists generated, games supported)
- `GET  /api/games/` — List supported games
- `GET  /api/games/{game_id}/playstyles` — Playstyles for a game
- `POST /api/specs/parse` — Parse hardware specs text
- `POST /api/modlist/generate` — Generate AI-powered mod list
- `GET  /api/modlist/mine` — Get current user's mod lists (auth required)
- `GET  /api/modlist/{modlist_id}` — Retrieve mod list
- `POST /api/downloads/start` — Start downloading mods
- `GET  /api/downloads/{modlist_id}/status` — Download progress
- `WS   /api/downloads/{modlist_id}/ws` — Real-time download progress (WebSocket)
- `GET  /api/settings/` — Get user settings (auth required)
- `PUT  /api/settings/` — Update user settings (auth required)
- `POST /api/auth/register` — Register new user
- `POST /api/auth/login` — Login (returns JWT + refresh cookie)
- `POST /api/auth/refresh` — Refresh access token
- `POST /api/auth/logout` — Logout (revokes refresh token)
- `GET  /api/auth/me` — Get current user profile
- `PUT  /api/auth/me` — Update profile
- `GET  /api/auth/me/hardware` — Get saved hardware specs
- `PUT  /api/auth/me/hardware` — Save hardware specs
- `POST /api/auth/verify-email` — Verify email with token
- `POST /api/auth/resend-verification` — Resend email verification (auth required)
- `POST /api/auth/forgot-password` — Request password reset email
- `POST /api/auth/reset-password` — Reset password with token
- `POST /api/auth/change-password` — Change password (auth required)
- `GET  /api/auth/oauth/providers` — List configured OAuth providers
- `GET  /api/auth/oauth/{provider}` — Start OAuth flow (google/discord)
- `GET  /api/auth/oauth/{provider}/callback` — OAuth callback

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to main:
- Backend: ruff lint (hard-fail), mypy type check (continue-on-error), pytest (hard-fail; only "no tests found" is suppressed)
- Frontend: ng lint (continue-on-error), production build

Render auto-deploys from `main` branch on push. Blueprint (`render.yaml`) defines all services.

Community files: `.github/CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/` (bug_report, feature_request)

## Content Filtering Note

When generating code or text related to custom mod sources, use generic terms like "custom mod source" or "Custom API Source" rather than naming specific adult content sites. The Anthropic API will block responses containing explicit site references.
