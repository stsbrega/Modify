# ModdersOmni — Implementation Plan

## Overview
Three major improvements: (1) smarter mod selection with game version awareness, (2) richer hardware tier classification, (3) gaming-themed dynamic UI. Plus a completed deployment migration from Railway to Render.

---

## 1. Mod Selection Logic — Game Version Awareness & Deeper Curation

> **Status: Completed**

### Problem
- Current mod selection only filters by VRAM threshold and playstyle, with no game version awareness
- Skyrim SE vs AE and Fallout 4 standard vs Next-Gen Update have different mod compatibility
- The LLM prompt doesn't mention game version, and the seed data has no version metadata

### What Was Implemented

#### Backend — Data Model
- **`Game` model** (`backend/app/models/game.py:22`): `versions` field (JSON list, e.g. `["SE", "AE"]` for Skyrim, `["Standard", "Next-Gen"]` for Fallout 4)
- **`Mod` model** (`backend/app/models/mod.py:25`): `game_version_support` field (String, e.g. `"all"`, `"se_only"`, `"ae_required"`, `"pre_nextgen"`, `"nextgen_only"`)
- **`ModlistGenerateRequest` schema** (`backend/app/schemas/modlist.py:8`): `game_version: str | None = None` field
- **`HardwareSpecs` schema** (`backend/app/schemas/specs.py:13-14`): `cpu_cores: int | None` and `cpu_speed_ghz: float | None` fields

#### Backend — Seed Data
- **`seed_data.py`**: Games include `versions` list. Mods include `game_version_support` values. Expanded mod database per game.

#### Backend — Mod Selection Logic
- **`modlist_generator.py`**: `_is_version_compatible()` function filters mods by version. LLM prompt includes version context. Fallback modlist also filters by version.
- **`api/modlist.py`**: Passes `game_version` through to generator. Added `GET /modlist/mine` for user's saved modlists.

#### Frontend
- **`game.model.ts`**: `versions?: string[]` on `Game` interface
- **`setup.component.ts:55-68`**: Version selection sub-step after game pick with styled version cards, `selectedGameVersion` signal
- **`playstyle-select.component.ts`**: Includes `game_version` in generate request
- **`api.service.ts`**: `generateModlist()` accepts `game_version`

---

## 2. Hardware Tier Classification — Multi-Factor Scoring

> **Status: Completed**

### Problem
- Current tier classification is VRAM-only (low=0, mid=6GB, high=10GB, ultra=16GB)
- No consideration of CPU cores/speed, RAM amount, or GPU generation (architecture age)
- A user with a GTX 1080 Ti (11GB VRAM) gets classified the same as an RTX 3080 (10GB) despite massive perf difference

### What Was Implemented

#### Backend — Tier Classifier Service
- **`backend/app/services/tier_classifier.py`** (168 lines):
  - `classify_hardware_tier(gpu, vram_mb, cpu, ram_gb, cpu_cores, cpu_speed_ghz) -> dict` returning tier and per-dimension scores
  - **VRAM scoring** (0-30 pts), **GPU generation scoring** (0-25 pts), **CPU scoring** (0-25 pts), **RAM scoring** (0-20 pts)
  - GPU generation database: NVIDIA (RTX 50xx down to GTX 900 series), AMD (RX 9000 down to RX 400/500), Intel Arc
  - **Tier thresholds**: Low=0-30, Mid=31-55, High=56-75, Ultra=76-100

#### Backend — Spec Parser Updates
- **`spec_parser.py`**: Regex patterns for CPU core count and speed. Returns `cpu_cores` and `cpu_speed_ghz` in `HardwareSpecs`

#### Backend — Integration
- **`modlist_generator.py`**: Uses `classify_hardware_tier()` for tier-aware prompts and VRAM budget
- **`api/modlist.py`**: Tier classification result included in response metadata

#### Frontend — Hardware Badge
- **`spec-input.component.ts:79-109`**: Colored tier badge with per-dimension score breakdown (VRAM, GPU gen, CPU, RAM bars)
- **`specs.model.ts:23`**: `TierScores` interface with `vram`, `cpu`, `ram`, `gpu_gen`, `overall` fields

---

## 3. UI Redesign — Dynamic Gaming Themes

> **Status: In Progress**

### Problem
- Current UI is generic dark theme with indigo accents — looks like a SaaS dashboard, not a gaming app
- Game cards show just a letter icon, no game imagery or atmosphere
- Buttons are generic ("Build Modlist", "Create New Modlist") — not immersive

### What's Done

- **Theme service** (`frontend/src/app/core/services/theme.service.ts`): Injectable singleton with `setTheme('skyrim' | 'fallout' | 'none')` and `currentTheme` signal. Applies/removes `.theme-skyrim` / `.theme-fallout` classes on `document.body`
- **Gaming terminology implemented across components**:
  - Modlist page: "Your Loadout", "Deploy Mods", "Forge New Loadout" (`modlist.component.ts`)
  - Downloads page: "Deployment", "Return to Loadout" (`downloads.component.ts`)
  - Spec input: "Scan Hardware" (`spec-input.component.ts`)
  - Header: "New Build" nav link (`header.component.ts`)
  - Dashboard: "New Build" button (`dashboard.component.ts`)
- **Setup wizard**: Version selection cards with styled UI (`setup.component.ts`)
- **Tier badge**: Score breakdown display in spec-input

### What Remains

#### Global Styles — Theme System
- **`styles.scss`**: Add `.theme-skyrim` and `.theme-fallout` CSS variable overrides:
  - **Skyrim theme**: Nordic blue/silver palette. `--color-primary: #4a8db7` (frost blue), `--color-bg-dark: #0a0f1a`, `--color-accent: #c9a84c` (gold)
  - **Fallout theme**: Wasteland green/amber palette. `--color-primary: #4ade80` (pip-boy green), `--color-bg-dark: #0c0f0a`, `--color-accent: #f59e0b` (amber)
- Add gaming fonts: Import "Rajdhani" as heading font

#### Header Redesign
- **`header.component.ts`**: Remaining nav link renames — "HQ" (dashboard), "Armory" (downloads), "Config" (settings). Logo glow effect. Theme class binding.

#### Dashboard Redesign
- **`dashboard.component.ts`**: Hero copy still says "Welcome back" — should be "Forge Your Perfect Modlist". Game cards need gradient backgrounds and version tags.

#### Settings Page
- **`settings.component.ts`**: Title "Configuration" with gear icon. Section headers with game-themed accents.

---

## 4. Deployment — Railway → Render Migration

> **Status: Completed (2026-02-19)**

### Problem
- Railway deployment relied on Docker Compose, nginx reverse proxy, and container networking
- nginx added complexity for a static Angular SPA that doesn't need a runtime server
- Docker builds were slower and harder to debug than native runtimes

### What Was Implemented

#### Removed Files
- `docker-compose.yml` — no longer needed for deployment
- `backend/Dockerfile`, `backend/.dockerignore` — replaced by Render's native Python runtime
- `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/docker-entrypoint.sh` — replaced by Render's static site hosting

#### Render Blueprint (`render.yaml`)
- **PostgreSQL 16** database (`moddersomni-db`) — Render managed, internal access only
- **Backend** — Python 3.12 native runtime. Render provides `PORT` env var. Start command transforms Render's `postgres://` connection string to `postgresql+asyncpg://` format. Pre-deploy command runs seed script.
- **Frontend** — Static site. Build command generates `env-config.js` with `API_URL` from env var before Angular production build. Render handles SPA routing via rewrite rules (no nginx needed). Asset caching headers configured in blueprint.

#### Environment Variables
- `DATABASE_URL_RAW` auto-populated from Render's database reference, transformed at runtime to asyncpg format
- `SECRET_KEY` auto-generated by Render
- API keys and OAuth secrets set manually in Render dashboard (`sync: false`)
- `API_URL` on frontend set to backend's public Render URL + `/api`
- `CORS_ORIGINS` and `FRONTEND_URL` on backend set to frontend's public Render URL

#### Frontend `env-config.js` Injection
- Previously: Docker entrypoint script generated `env-config.js` at container start (runtime injection)
- Now: Render build command generates `env-config.js` before `ng build` (build-time injection)
- `ApiService` reads `window.__env.API_URL` unchanged — no application code changes needed
- Local dev still uses `proxy.conf.json` with `/api` fallback

---

## File Change Summary

### Files Created During Implementation
1. `backend/app/services/tier_classifier.py` — Multi-factor hardware classification (168 lines)
2. `frontend/src/app/core/services/theme.service.ts` — Dynamic theme management

### Modified Files (Backend — 8 files)
3. `backend/app/models/game.py` — Added `versions` JSON field
4. `backend/app/models/mod.py` — Added `game_version_support` field
5. `backend/app/schemas/modlist.py` — Added `game_version` to request
6. `backend/app/schemas/specs.py` — Added `cpu_cores`, `cpu_speed_ghz`, tier fields
7. `backend/app/services/spec_parser.py` — Parses CPU cores/speed
8. `backend/app/services/modlist_generator.py` — Version filtering, tier-aware prompts
9. `backend/app/api/modlist.py` — Passes version, returns tier info, added `GET /mine`
10. `backend/app/seeds/seed_data.py` — Version metadata, expanded mod database

### Modified Files (Frontend — 11 files)
11. `frontend/src/styles.scss` — Pending: theme CSS variables, gaming fonts
12. `frontend/src/app/shared/models/game.model.ts` — Added versions to Game
13. `frontend/src/app/shared/models/specs.model.ts` — Added TierScores
14. `frontend/src/app/shared/components/header/header.component.ts` — Partial: "New Build" done, remaining nav renames pending
15. `frontend/src/app/core/services/api.service.ts` — Added game_version param
16. `frontend/src/app/features/dashboard/dashboard.component.ts` — Pending: hero copy, gradient cards
17. `frontend/src/app/features/setup/setup.component.ts` — Version selection, theme switching
18. `frontend/src/app/features/setup/steps/game-select/game-select.component.ts` — Version selection, themed cards
19. `frontend/src/app/features/setup/steps/spec-input/spec-input.component.ts` — Tier badge, "Scan Hardware"
20. `frontend/src/app/features/setup/steps/playstyle-select/playstyle-select.component.ts` — Themed cards, gaming buttons
21. `frontend/src/app/features/modlist/modlist.component.ts` — "Your Loadout", "Deploy Mods", "Forge New Loadout"
22. `frontend/src/app/features/downloads/downloads.component.ts` — "Deployment", "Return to Loadout"
23. `frontend/src/app/features/settings/settings.component.ts` — Pending: gaming terminology

### Remaining Work (Section 3 only)
- `frontend/src/styles.scss` — Theme CSS variables for `.theme-skyrim` / `.theme-fallout`, Rajdhani font import
- `frontend/src/app/shared/components/header/header.component.ts` — Nav renames (HQ, Armory, Config), logo glow
- `frontend/src/app/features/dashboard/dashboard.component.ts` — Hero copy, gradient game cards
- `frontend/src/app/features/settings/settings.component.ts` — "Configuration" title, themed accents
