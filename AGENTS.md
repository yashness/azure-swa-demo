# AGENTS.md - AI Coding Agent Guidelines

This document provides guidelines for AI coding agents working on this project.

## Project Overview

This is a full-stack Azure deployment demo with:
- **Frontend**: Vite + Bun + TypeScript → Azure Static Web Apps
- **Backend**: FastAPI + SQLite + uv (Python 3.14) → Azure App Service

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
| Python | 3.14 | Runtime |
| uv | Latest | Package manager (by Astral) |
| FastAPI | 0.128+ | Web framework |
| SQLAlchemy | 2.x | ORM |
| SQLite | 3 | Database |
| Uvicorn | Latest | ASGI server (dev) |
| Gunicorn | Latest | WSGI server (prod) |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Azure Static Web Apps | Frontend hosting |
| Azure App Service | Backend hosting |
| GitHub Actions | CI/CD |
| DevContainer | Development environment |

## Code Guidelines

### Frontend (TypeScript/Vite)

```typescript
// Prefer typed interfaces
interface User {
  id: number
  name: string
  email: string
}

// Use environment variables for API URL
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
├── frontend/           # Vite/Bun frontend
│   ├── src/           # Source files
│   ├── public/        # Static assets
│   └── dist/          # Build output (gitignored)
├── backend/           # FastAPI backend
│   ├── main.py        # Main application
│   ├── .venv/         # Virtual environment (gitignored)
│   └── *.db           # SQLite database (gitignored)
├── .devcontainer/     # DevContainer configuration
└── .github/workflows/ # CI/CD pipelines
```

## Common Tasks

### Add a new API endpoint
1. Edit `backend/main.py`
2. Add route with proper type hints
3. Test locally with `uv run uvicorn main:app --reload`
4. Update API documentation in README

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
```

### Run locally

**Full stack:**
```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && bun run dev
```

## Environment Variables

### Frontend
| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

### Backend
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite connection | `sqlite:///./users.db` |

## Deployment Notes

### Frontend (Azure Static Web Apps)
- Build output: `frontend/dist`
- No API functions (separate backend)
- Configure CORS on backend for SWA URL

### Backend (Azure App Service)
- Python 3.14 runtime
- Startup command: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`
- Enable SCM_DO_BUILD_DURING_DEPLOYMENT for automatic pip install

## Testing

### Frontend
```bash
cd frontend && bun run build  # Type checking + build
```

### Backend
```bash
cd backend && uv run python -c "from main import app; print('OK')"
```

## Troubleshooting

### Port already in use
```bash
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000
lsof -ti:5173 | xargs kill -9  # Kill process on port 5173
```

### Database reset
```bash
cd backend && rm -f users.db && uv run uvicorn main:app
```

### Dependency issues
```bash
# Frontend
cd frontend && rm -rf node_modules bun.lock && bun install

# Backend
cd backend && rm -rf .venv uv.lock && uv sync
```
