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

## Google OAuth 2.0 Reference

This section documents the Google OAuth 2.0 Authorization Code flow as implemented in this project. The app uses `authlib` (not Google's client library) to interact directly with Google's OAuth 2.0 protocol endpoints.

### Our OAuth Flow (step by step)

1. **Frontend** calls `GET /api/auth/oauth/google` → backend generates a random `state` token (UUID, stored in-memory with 10-min TTL), builds the authorization URL, returns `{ authorization_url, state }`.
2. **Frontend** redirects the user's browser to Google's authorization endpoint.
3. **Google** prompts the user for consent, then redirects back to our **backend** callback URL with `?code=...&state=...`.
4. **Backend** (`GET /api/auth/oauth/google/callback`) validates `state` against the in-memory store (CSRF protection), then exchanges the `code` for tokens by POSTing to Google's token endpoint.
5. **Backend** uses the access token to fetch user info from Google's userinfo endpoint.
6. **Backend** creates or links the user account, issues our own JWT + refresh token, then **redirects** to `{FRONTEND_URL}/auth/callback?token={access_token}` (with refresh token set as an HTTP cookie).
7. **Frontend** `AuthCallbackComponent` extracts the `token` query param, saves it via `AuthService`, loads the user profile, and navigates to `/dashboard`.

### Google OAuth 2.0 Endpoints

| Purpose | URL |
|---------|-----|
| Authorization | `https://accounts.google.com/o/oauth2/v2/auth` |
| Token exchange | `https://oauth2.googleapis.com/token` |
| User info | `https://www.googleapis.com/oauth2/v3/userinfo` |
| Token revocation | `https://oauth2.googleapis.com/revoke` |

### Authorization Request Parameters

| Parameter | Required | Our Value / Notes |
|-----------|----------|-------------------|
| `client_id` | **Yes** | From `GOOGLE_CLIENT_ID` env var. Configured in [Google Cloud Console → Clients](https://console.developers.google.com/auth/clients). |
| `redirect_uri` | **Yes** | Must **exactly match** one of the authorized redirect URIs registered in the Google Cloud Console (scheme, case, trailing slash all matter). See Redirect URI Rules below. |
| `response_type` | **Yes** | `code` (authorization code flow). |
| `scope` | **Yes** | `openid email profile` — we only need basic identity info, not access to Google APIs. |
| `state` | **Recommended** | Random UUID for CSRF protection. Our backend stores it in-memory with a 10-min TTL and validates on callback. |
| `access_type` | Recommended | We do **not** currently set this (defaults to `online`). Set to `offline` if we ever need Google refresh tokens. |
| `prompt` | Optional | Not currently set. Use `consent` to force re-consent, `select_account` to force account chooser. |
| `login_hint` | Optional | Not currently set. Can pass an email to pre-fill the sign-in form. |
| `include_granted_scopes` | Optional | Not currently set. Set to `true` to enable incremental authorization (scopes accumulate across grants). |

### Token Exchange Parameters (POST to token endpoint)

| Field | Value |
|-------|-------|
| `client_id` | `GOOGLE_CLIENT_ID` |
| `client_secret` | `GOOGLE_CLIENT_SECRET` |
| `code` | The authorization code from the callback query string |
| `grant_type` | `authorization_code` |
| `redirect_uri` | Must match the one used in the authorization request |

Successful response returns `{ access_token, expires_in, token_type, scope }` (plus `refresh_token` if `access_type=offline` was set on the initial request).

### Redirect URI Configuration

| Environment | Redirect URI | Set In |
|-------------|-------------|--------|
| Local dev | `http://localhost:8000/api/auth/oauth/google/callback` | `config.py` default |
| Production | `https://moddersomni-api.onrender.com/api/auth/oauth/google/callback` | `render.yaml` (`GOOGLE_REDIRECT_URI`) |

**Both** URIs must be registered as authorized redirect URIs in the [Google Cloud Console → Clients page](https://console.developers.google.com/auth/clients).

### Redirect URI Validation Rules (Google-enforced)

- **HTTPS required** — except `localhost` URIs which may use HTTP.
- **Exact match** — scheme, host, port, path, case, and trailing slash must all match exactly.
- **No raw IP addresses** — except `localhost` IPs.
- **No wildcards** (`*`), no fragments (`#`), no path traversals (`/..`), no userinfo (`user@`).
- **No URL shortener domains** (e.g., `goo.gl`).
- **Host TLD** must be on the [public suffix list](https://publicsuffix.org/list/).
- **Cannot be** `googleusercontent.com`.
- **No open redirects** in query parameters.

### Common Google OAuth Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `redirect_uri_mismatch` | The `redirect_uri` sent in the auth request doesn't exactly match any URI registered in Google Cloud Console. | Verify scheme (http vs https), exact path, trailing slashes. Check both local and production URIs are registered. |
| `invalid_client` | Wrong client secret. | Re-check `GOOGLE_CLIENT_SECRET` env var matches the Cloud Console value. Client secrets are only shown once at creation; can't be re-viewed. |
| `invalid_grant` | Authorization code is expired, already used, or tokens were revoked. | Restart the OAuth flow from the beginning. Codes are single-use and short-lived. |
| `deleted_client` | OAuth client was deleted (manually or auto-cleanup for unused clients). | Restore within 30 days from Cloud Console, or create a new client. |
| `admin_policy_enforced` | Google Workspace admin has blocked the app or specific scopes. | Contact the Workspace admin to allowlist the OAuth client ID. |
| `disallowed_useragent` | Auth endpoint opened in an embedded webview (e.g., iOS WKWebView). | Open in the default system browser instead. |
| `org_internal` | OAuth client is set to "Internal" user type, blocking external Google accounts. | Change to "External" in Cloud Console → OAuth consent screen, or the user must be in the same Google Cloud org. |
| `access_denied` | User declined the consent prompt. | Handle gracefully in UI — show a message and let the user retry. |
| `invalid_request` | Malformed request, missing required params, or unsupported auth method. | Verify all required parameters are present and correctly formatted. |

### Google Cloud Console Setup Checklist

1. Go to [Google Cloud Console → APIs & Services → Clients](https://console.developers.google.com/auth/clients).
2. Create an OAuth 2.0 Client ID with application type **Web application**.
3. Add **both** redirect URIs (local + production) to the authorized redirect URIs list.
4. Copy the `Client ID` and `Client Secret` — the secret is only shown once.
5. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` (local) or Render dashboard (production, `sync: false`).
6. Ensure the OAuth consent screen is configured (app name, support email, authorized domains).
7. For production with external users: submit for verification if using sensitive/restricted scopes (our `openid email profile` scopes are non-sensitive).

### Token & Session Notes

- We do **not** store Google tokens — we only use them transiently to fetch the user's profile during the callback, then issue our own JWT.
- Google access tokens expire in ~1 hour. Since we don't store them, this doesn't affect us.
- Google refresh tokens (if `access_type=offline` were used) are only returned on the **first** authorization. Subsequent authorizations return only access tokens unless `prompt=consent` forces re-consent.
- Our in-memory OAuth state store (`_oauth_states` dict in `services/oauth.py`) is **not shared across backend instances**. If running multiple backend replicas, replace with a shared store (Redis, database).
- The frontend callback route is `/auth/callback` — this is an Angular route, not registered with Google. Google only redirects to the **backend** callback URI.

## Content Filtering Note

When generating code or text related to custom mod sources, use generic terms like "custom mod source" or "Custom API Source" rather than naming specific adult content sites. The Anthropic API will block responses containing explicit site references.
