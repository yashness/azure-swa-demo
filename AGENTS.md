# AGENTS.md - AI Coding Agent Guidelines

This document provides guidelines for AI coding agents working on this project.

## Project Overview

This is a full-stack Azure deployment demo with:
- **Frontend**: Vite + Bun + TypeScript → Azure Static Web Apps
- **Backend**: FastAPI + PostgreSQL (Neon) + uv (Python 3.12) → Azure App Service
- **Database**: Neon PostgreSQL (serverless) for production, SQLite for local dev

## Technology Choices

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Bun | Latest | JavaScript runtime & package manager |
| Vite | 7.x | Build tool & dev server |
| TypeScript | 5.x | Type safety |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Runtime |
| uv | Latest | Package manager (by Astral) |
| FastAPI | 0.128+ | Web framework |
| SQLAlchemy | 2.x | ORM |
| psycopg2-binary | 2.9+ | PostgreSQL driver |
| Uvicorn | Latest | ASGI server (dev) |
| Gunicorn | Latest | ASGI server (prod) |

### Database
| Environment | Database | Notes |
|-------------|----------|-------|
| Local Dev | SQLite | Zero config, fast iteration |
| Production | Neon PostgreSQL | Serverless, free tier available |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Azure Static Web Apps | Frontend hosting (CDN + HTTPS) |
| Azure App Service | Backend hosting (Linux + Python) |
| Neon PostgreSQL | Serverless PostgreSQL database |
| GitHub Actions | CI/CD |

## ⚠️ Critical Gotchas

### 1. Backend File MUST be `application.py`
Azure Oryx auto-detection looks for `application.py` or `app.py`, NOT `main.py`.
```bash
# ❌ Wrong: main.py → Azure shows default page
# ✅ Correct: application.py → Azure runs your app
```

### 2. Always Generate requirements.txt
Azure uses `requirements.txt`, not `pyproject.toml`:
```bash
cd backend && uv pip compile pyproject.toml -o requirements.txt
```

### 3. String Columns Need Explicit Length
PostgreSQL requires length for VARCHAR:
```python
# ❌ Wrong: String() - fails on PostgreSQL
# ✅ Correct: String(100) - works everywhere
name = Column(String(100), index=True)
```

### 4. Neon Cold Start Handling
Free tier sleeps after inactivity. App has retry logic and 60s+ timeouts.

## Code Guidelines

### Frontend (TypeScript/Vite)

```typescript
// Prefer typed interfaces
interface User {
  id: number
  name: string
  email: string
}

// Use environment variables for API URL (MUST have VITE_ prefix!)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Use async/await for API calls
async function fetchUsers(): Promise<User[]> {
  const response = await fetch(`${API_URL}/users`)
  return response.json()
}
```

### Backend (Python/FastAPI)

```python
# Use type hints
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Use dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use async endpoints when possible
@app.get("/users")
async def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

## Directory Structure

```
/
├── frontend/              # Vite/Bun frontend
│   ├── src/               # Source files
│   ├── public/            # Static assets
│   ├── dist/              # Build output (gitignored)
│   ├── .env.development   # Local API URL
│   ├── .env.production    # Prod API URL (template)
│   └── .env.example       # Template for developers
├── backend/               # FastAPI backend
│   ├── application.py     # ⚠️ Main app (NOT main.py!)
│   ├── pyproject.toml     # Dependencies definition
│   ├── requirements.txt   # Generated dependencies (for Azure)
│   ├── .venv/             # Virtual environment (gitignored)
│   ├── .env               # Local secrets (gitignored)
│   ├── .env.example       # Template for developers
│   └── *.db               # SQLite database (gitignored)
├── docs/                  # Documentation
│   ├── FULLSTACK_DEPLOYMENT_GUIDE.md  # Complete deployment guide
│   └── AZURE_DEPLOYMENT_GUIDE.md      # Original SQLite guide
├── .github/workflows/     # CI/CD pipelines
└── AGENTS.md              # This file
```

## Common Tasks

### Add a new API endpoint
1. Edit `backend/application.py`
2. Add route with proper type hints
3. Test locally with `uv run uvicorn application:app --reload`
4. Update API documentation

### Add a new frontend feature
1. Edit files in `frontend/src/`
2. Test locally with `bun run dev`
3. Ensure TypeScript compiles: `bun run build`

### Update dependencies

**Frontend:**
```bash
cd frontend && bun update
```

**Backend:**
```bash
cd backend && uv add <package>
uv pip compile pyproject.toml -o requirements.txt  # Regenerate!
```

### Run locally

**Full stack:**
```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn application:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && bun run dev
```

## Environment Variables

### Frontend
| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

⚠️ **MUST use `VITE_` prefix** for client-side variables!

### Backend
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./dev.db` |
| `DEBUG` | Debug mode | `true` |

**Local SQLite:**
```
DATABASE_URL=sqlite:///./dev.db
```

**Production (Neon):**
```
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
```

## Deployment

### Startup Command (Azure App Service)
```bash
gunicorn application:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
```

Key points:
- `application:app` - file must be `application.py`
- `--workers 1` - safe for SQLite, can increase for PostgreSQL
- `--timeout 120` - handles Neon cold starts

### Quick Deploy
```bash
# Backend
cd backend && az webapp up --name YOUR_APP_NAME --runtime "PYTHON:3.12"

# Frontend (via CI/CD)
git push origin main  # Triggers GitHub Actions
```

## Testing

### Frontend
```bash
cd frontend && bun run build  # Type checking + build
```

### Backend
```bash
cd backend && uv run python -c "from application import app; print('OK')"
```

## Troubleshooting

### Port already in use
```bash
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000
lsof -ti:5173 | xargs kill -9  # Kill process on port 5173
```

### Database reset (local)
```bash
cd backend && rm -f dev.db && uv run uvicorn application:app
```

### Dependency issues
```bash
# Frontend
cd frontend && rm -rf node_modules bun.lock && bun install

# Backend
cd backend && rm -rf .venv uv.lock && uv sync
uv pip compile pyproject.toml -o requirements.txt
```

### Check Azure logs
```bash
az webapp log tail --name YOUR_APP_NAME --resource-group YOUR_RG_NAME
```

## Links

- **Frontend**: https://icy-tree-076e2650f.2.azurestaticapps.net
- **Backend**: https://azure-swa-demo-api.azurewebsites.net
- **Neon Dashboard**: https://console.neon.tech
- **Deployment Guide**: [docs/FULLSTACK_DEPLOYMENT_GUIDE.md](docs/FULLSTACK_DEPLOYMENT_GUIDE.md)
