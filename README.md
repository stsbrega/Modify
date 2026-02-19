# ModdersOmni

AI-powered video game mod manager that analyzes your PC hardware and builds custom, stable modlists tailored to your playstyle.

## Features

- **Hardware-Aware Modlists** - Paste your PC specs and ModdersOmni classifies your hardware tier to recommend mods your system can handle
- **Playstyle Presets** - Choose from popular playstyles (Survival, Combat Overhaul, Visual Enhancement, etc.) and get a curated modlist
- **AI-Powered Curation** - Uses open-source LLMs (local via Ollama or free cloud APIs) to generate compatible, conflict-free modlists
- **Nexus Mods Integration** - Search, browse, and download mods directly via the Nexus Mods API
- **Custom Mod Sources** - Add additional mod sources beyond Nexus Mods via custom API endpoints
- **Load Order Management** - Automatic load order sorting based on compatibility rules
- **One-Click Downloads** - Download your entire modlist with progress tracking

## Supported Games

- The Elder Scrolls V: Skyrim Special Edition / Anniversary Edition
- Fallout 4

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Angular 19, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| AI/LLM | Ollama (local), Groq, Together AI, HuggingFace (cloud) |
| Mod APIs | Nexus Mods v2 (GraphQL), Custom Sources |

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Node.js](https://nodejs.org/) 20+ (for frontend development)
- [Python](https://www.python.org/) 3.11+ (for backend development)
- A [Nexus Mods](https://www.nexusmods.com/) account (free API key)

### Running with Docker

```bash
git clone https://github.com/YOUR_USERNAME/modify.git
cd modify
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
docker-compose up -d
```

- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
ng serve
```

## LLM Configuration

ModdersOmni supports multiple LLM providers. Choose one based on your setup:

| Provider | Cost | Requirements | Model |
|----------|------|-------------|-------|
| Ollama (Local) | Free | 8GB+ RAM, local install | llama3.1:8b, mistral:7b |
| Groq | Free tier | API key | llama-3.3-70b-versatile |
| Together AI | Free tier | API key | Llama-3.3-70B-Instruct-Turbo-Free |
| HuggingFace | Free tier | API key | Various |

Configure your preferred provider in the Settings page or via `backend/.env`.

## Project Structure

```
modify/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── llm/       # LLM provider abstraction
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   └── alembic/       # Database migrations
├── frontend/          # Angular 19 SPA
│   └── src/app/
│       ├── core/      # Services, interceptors
│       ├── shared/    # Reusable components, models
│       └── features/  # Feature modules (dashboard, setup, modlist, etc.)
├── docs/              # Documentation
└── docker-compose.yml
```

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Nexus Mods](https://www.nexusmods.com/) for their modding platform and API
- [LOOT](https://loot.github.io/) for load order optimization research
- [Ollama](https://ollama.ai/) for local LLM inference
