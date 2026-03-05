# ModdersOmni

AI-powered video game modding assistant that analyzes your PC hardware and builds custom, stable modlists tailored to your playstyle.

## Features

- **Hardware-Aware Modlists** — ModdersOmni reads your saved hardware profile (GPU generation, VRAM, CPU, RAM, SSD space) to recommend mods your system can handle
- **Game Version Intelligence** — Distinguishes between Skyrim SE/AE and Fallout 4 Standard/Next-Gen to filter mods by compatibility
- **Freeform Playstyle Prompts** — Describe what you want in plain language (e.g., "dark fantasy with survival mechanics and Legacy of the Dragonborn") and the AI interprets your intent into mod selection logic. Specific mod requests are treated as priority inclusions. Prompts are capped at 200 words (~270 tokens) to maintain efficient context usage
- **Past Playstyle Analysis** — The AI analyzes your previous modlist builds for the same game to inform suggestions for new builds, helping refine recommendations over time
- **AI-Powered Curation** — Uses 9 LLM providers (Anthropic, OpenAI, Gemini, Groq, Together AI, DeepSeek, Mistral, Qwen, OpenRouter) via an OpenAI-compatible client to generate compatible, conflict-free modlists through a 13-phase build methodology with post-build verification auditing
- **Multi-Provider Fallback** — Configure multiple LLM API keys; if one provider hits a rate limit or errors during generation, the system automatically falls back to the next configured provider for resilient modlist generation
- **Dynamic Key Detection** — The settings page detects which LLM provider an API key belongs to automatically, so users can paste any key without manually selecting the provider
- **API Key Guide** — Expandable help section in Settings and Setup wizard explaining how to obtain API keys, recommending free and paid providers, and explaining the benefit of multiple keys
- **Nexus Mods Integration** — Search, browse, and download mods directly via the Nexus Mods v2 GraphQL API
- **User Accounts & OAuth** — Register with email or sign in with Google/Discord, save hardware profiles, and access your modlist history
- **Inactive Account Cleanup** — Users inactive for 1 year receive a warning email, then have their account and stored data automatically deleted after 30 additional days to protect unused API keys and personal data
- **Load Order Management** — Automatic load order sorting based on compatibility rules
- **One-Click Downloads** — Download your entire modlist with real-time progress tracking via WebSockets

## Modlist Build Workflow

1. **Select Game** — Choose Skyrim (SE or AE) or Fallout 4 (Standard or Next-Gen). This determines which game-specific knowledge base is injected into the LLM context.

2. **Hardware Verification** — The system loads the user's saved hardware profile (GPU, VRAM, CPU, RAM, available SSD space). These specs drive VRAM budget checks, texture resolution recommendations, and SSD space validation throughout the build.

3. **Describe Your Playstyle** — The user writes a freeform prompt describing what they want from their modlist (capped at 200 words). The AI interprets natural language into modlist building logic — mapping phrases like "good graphics" to the appropriate Nexus categories and phases. Users can also name specific mods they want included, which are treated as priority selections. The AI presents a suggested approach that can be iteratively refined until the user is satisfied.

4. **Past Playstyle Context** — For returning users, the AI analyzes previous modlist builds for the selected game to inform suggestions. This context is game-specific and injected alongside the knowledge base with a word limit to control token usage.

5. **Generate Modlist** — Once the user confirms their playstyle, the AI builds the modlist through 13 sequential phases (defined in the knowledge base), checking Nexus mod requirements at each selection, then runs a post-build verification audit covering dependency completeness, version consistency, mutual exclusivity, plugin count, VRAM budget, SSD space, and game-specific safety checks.

## Knowledge Base Architecture

The modding knowledge base is split into three files optimized for LLM context injection:

| File | Purpose | Injected When |
|------|---------|---------------|
| `modding_common.md` | Universal engine principles, 13 build phases, conflict patterns, plugin limits, VRAM tables, mod selection rules, post-build audit | Always |
| `skyrim.md` | SE/AE version matrix, Nexus category mappings, Phase 1 essentials, animation frameworks, weather/lighting rules, load order sequence, Skyrim-specific conflicts and prohibitions | Skyrim builds |
| `fallout4.md` | OG/NG version matrix, Nexus category mappings, Phase 1 essentials, precombine/previs system, BA2 rules, AWKCR deprecation, FO4-specific conflicts and prohibitions | Fallout 4 builds |

**Injection strategy:** For Skyrim builds, inject `modding_common.md` + `skyrim.md`. For Fallout 4 builds, inject `modding_common.md` + `fallout4.md`. This eliminates cross-game duplication while keeping per-game token cost under ~4,700 tokens.

The files use a hybrid Markdown + XML tag format: XML tags (`<section_name>`) provide semantic boundaries for LLM section recognition, while Markdown handles content within sections for maximum token efficiency. Each concept lives in exactly one location — common defines universal rules, game files contain only game-specific details that differ from or extend the common rules.

## Supported Games

- The Elder Scrolls V: Skyrim Special Edition / Anniversary Edition
- Fallout 4 (Standard / Next-Gen)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Angular 19, Tailwind CSS 4, TypeScript 5.7 |
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2 |
| Database | PostgreSQL 16 (asyncpg) |
| Auth | JWT + refresh tokens, bcrypt, OAuth (Google, Discord), email verification |
| AI/LLM | 9 providers: Anthropic, OpenAI, Gemini, Groq, Together AI, DeepSeek, Mistral, Qwen, OpenRouter — OpenAI-compatible client |
| Mod APIs | Nexus Mods v2 (GraphQL), Custom Sources |
| Deployment | Render (Python runtime, static site, managed PostgreSQL) |

## Live App

ModdersOmni is live at **[moddersomni-web.onrender.com](https://moddersomni-web.onrender.com)**

## Legal Foundation & Methodology

ModdersOmni is built on a legally defensible approach to game modding assistance. This section outlines the principles guiding how the project sources its knowledge and interfaces with game engines.

### Knowledge Base Strategy

The project's knowledge base is built primarily on publicly available, community-validated resources rather than proprietary game code:

- **Official tools**: Bethesda's Creation Kit and its built-in documentation
- **Community documentation**: UESP Wiki, modding.wiki, and extensive community guides
- **Open-source community tools**: CommonLibSSE (class definitions), Address Library (function mappings), Champollion (Papyrus decompilation), xEdit (format documentation), and SKSE
- **Open-source LLMs**: All AI capabilities use openly available models — no proprietary training on copyrighted game code

This existing community knowledge base is substantial enough to build a powerful modding assistant without deep binary reverse engineering.

### Reverse Engineering Policy

When analysis beyond public documentation is necessary, ModdersOmni limits its scope to understanding functional interfaces — data formats, file structures, and API specifications. These elements are generally unprotectable under the idea/expression dichotomy (17 U.S.C. § 102(b); EU Directive Art. 1(2)). The project follows a clean-room methodology separating analysis from implementation, and never distributes reverse-engineered game code — only original code that interfaces with the game.

### Jurisdictional Considerations

The EU provides the strongest legal protections for this type of work through non-waivable decompilation rights for interoperability. The US offers robust fair use precedents. Canada falls in between with narrower exceptions. Across all jurisdictions, a clean-room approach and focus on functional interfaces over copyrighted expression remain the essential risk-mitigation strategies.

### Copyright & Source Code

Bethesda's game source code is protected by copyright until at least 2081 (and potentially 2110 under US law). Voluntary release is unlikely given the commercial value of these titles, middleware licensing constraints, and strategic importance of the Creation Engine. ModdersOmni does not depend on source code access — the combination of existing community knowledge with AI-powered analysis of targeted subsystems delivers substantial value to modders on a solid legal foundation.

## Project Structure

```
moddersomni/
├── backend/             # FastAPI backend
│   ├── app/
│   │   ├── api/         # Route handlers (auth, games, specs, modlist, downloads, settings, stats)
│   │   ├── llm/         # LLM provider abstraction (OpenAI-compatible)
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── schemas/     # Pydantic request/response schemas
│   │   ├── services/    # Business logic (auth, email, OAuth, spec parser, tier classifier, Nexus client, account cleanup)
│   │   │   └── generation/  # Modlist generation pipeline (manager, prompts, session, tools, version)
│   │   └── seeds/       # Database seed data
│   ├── alembic/         # Database migrations
│   ├── tests/           # pytest + pytest-asyncio
│   └── .env.example     # Environment variable reference
├── frontend/            # Angular 19 SPA
│   └── src/app/
│       ├── core/        # Services, interceptors, guards, utilities (key detection)
│       ├── shared/      # Reusable components (header, notification-toast, api-key-guide), models
│       └── features/    # Feature modules (landing, dashboard, setup, generation, modlist, downloads, browse, settings, auth)
├── render.yaml          # Render infrastructure blueprint
└── docs/                # Documentation
```

## Deployment

ModdersOmni is deployed on [Render](https://render.com) using a `render.yaml` infrastructure blueprint. The stack consists of a Python 3.12 backend, Angular static site frontend, and managed PostgreSQL 16 database.

To deploy your own instance: push to GitHub, then in Render Dashboard go to Blueprints → New Blueprint Instance. Environment variables marked `sync: false` in `render.yaml` (API keys, OAuth secrets) must be set manually after first deploy.

> **Note**: Ollama (local LLM) does not work on Render — use a cloud provider (Groq, Together AI, Gemini, etc.).

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the GPL-3.0 License — see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Nexus Mods](https://www.nexusmods.com/) for their modding platform and API
- [CommonLibSSE](https://github.com/Ryan-rsm-McKenzie/CommonLibSSE) and [SKSE](https://skse.silverlock.org/) for foundational modding infrastructure
- [LOOT](https://loot.github.io/) for load order optimization research
- The Bethesda modding community for decades of accumulated knowledge and open-source tooling
