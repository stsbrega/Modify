# CLAUDE.md

## Project Overview

Modify is an AI-powered game modding assistant that generates personalized mod lists based on hardware specs and gameplay preferences. It targets Skyrim SE/AE and Fallout 4.

## Tech Stack

- **Frontend**: Angular 19.2 (standalone components) + Tailwind CSS 4 + TypeScript 5.7
- **Backend**: Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2
- **Database**: PostgreSQL 16 (via asyncpg)
- **Auth**: JWT (python-jose) + bcrypt (passlib) + OAuth (authlib) + email verification (fastapi-mail)
- **Migrations**: Alembic (no migrations yet — seed script uses `create_all`)
- **LLM**: OpenAI-compatible client (`openai` SDK) — supports Ollama (local), Groq, Together AI, HuggingFace (cloud)
- **Mod API**: Nexus Mods v2 GraphQL API + optional custom mod source
- **Deployment**: Docker Compose (local), Railway (production)
- **License**: GPL-3.0

## Project Structure

```
backend/
  app/
    api/              # FastAPI route handlers
      auth.py         #   /auth/* — register, login, OAuth, email verify, password reset
      deps.py         #   JWT dependency injection (get_current_user, require_verified_email)
      games.py        #   GET /games/, GET /games/{game_id}/playstyles
      specs.py        #   POST /specs/parse
      modlist.py      #   POST /modlist/generate, GET /modlist/{modlist_id}
      downloads.py    #   POST /downloads/start, GET /downloads/{id}/status, WS /downloads/{id}/ws
      settings.py     #   GET /settings/, PUT /settings/ (requires auth)
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
    schemas/          # Pydantic request/response schemas (auth, game, modlist, specs)
    services/         # Business logic
      auth.py         #   JWT creation/validation, password hashing, token management
      email.py        #   SMTP email sending (verification, password reset)
      oauth.py        #   OAuth provider abstraction (Google, Discord, Apple)
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
  alembic/            # Migration config (versions/ is empty)
  tests/              # pytest + pytest-asyncio (SQLite in-memory test DB)
  .env.example        # Environment variable reference

frontend/
  src/app/
    core/
      services/       # ApiService, AuthService, NotificationService, ThemeService
      interceptors/   # AuthInterceptor, ErrorInterceptor
      guards/         # authGuard, guestGuard
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
  nginx.conf          # Nginx template (uses ${PORT} substitution)
  docker-entrypoint.sh # Runtime env injection (PORT, API_URL)
```

## Common Commands

### Backend (run from `backend/`)

```bash
pip install -r requirements.txt        # Install dependencies
uvicorn app.main:app --reload           # Dev server (localhost:8000)
pytest tests/ -v                        # Run tests
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

### Docker (run from repo root)

```bash
docker-compose up -d                    # Start full stack
# Frontend: http://localhost:4200
# Backend:  http://localhost:8000
# Swagger:  http://localhost:8000/docs
```

**Note**: Backend Dockerfile hardcodes port 8080 (for Railway). docker-compose maps `8000:8080` for local dev. For development, use uvicorn directly (not Docker) on port 8000.

## Code Conventions

### Backend
- Follow PEP 8; use `black` for formatting and `ruff` for linting
- Async endpoints throughout (async def, await)
- Models in `models/`, Pydantic schemas in `schemas/`, business logic in `services/`
- API routes prefixed with `/api/`
- Environment config via `.env` file (see `backend/.env.example`)
- Settings are per-user in the `user_settings` PostgreSQL table (requires authentication)
- LLM modlist generation falls back to curated DB mods if LLM call fails

### Frontend
- Angular 19 standalone component API (no NgModules)
- Feature components use inline templates/styles (single `.ts` files)
- Feature-based folder organization under `features/`
- Shared reusable components under `shared/components/`
- Core singleton services under `core/services/`
- Tailwind CSS for styling; SCSS for component-level styles
- Models defined as TypeScript interfaces in `shared/models/`
- API base URL: reads `window.__env.API_URL` (Docker) with fallback to `http://localhost:8000/api`

## API Endpoints

- `GET  /api/health` — Health check
- `GET  /api/games/` — List supported games
- `GET  /api/games/{game_id}/playstyles` — Playstyles for a game
- `POST /api/specs/parse` — Parse hardware specs text
- `POST /api/modlist/generate` — Generate AI-powered mod list
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
- `POST /api/auth/forgot-password` — Request password reset email
- `POST /api/auth/reset-password` — Reset password with token
- `GET  /api/auth/oauth/{provider}` — Start OAuth flow (google/discord/apple)
- `GET  /api/auth/oauth/{provider}/callback` — OAuth callback

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to main:
- Backend: ruff lint (hard-fail), mypy type check (continue-on-error), pytest (soft-fail)
- Frontend: ng lint (continue-on-error), production build
- Docker: Compose config validation (push to main only)

Community files: `.github/CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/` (bug_report, feature_request)

## Content Filtering Note

When generating code or text related to custom mod sources, use generic terms like "custom mod source" or "Custom API Source" rather than naming specific adult content sites. The Anthropic API will block responses containing explicit site references.

