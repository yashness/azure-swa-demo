# Fullstack Deployment Guide: Azure + Neon PostgreSQL

> **A prescriptive, step-by-step guide** for deploying Vite/Bun + FastAPI fullstack apps to Azure Static Web Apps + App Service with Neon PostgreSQL.

**Based on real deployment experience** - includes all pitfalls, gotchas, and solutions.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Naming Conventions](#2-naming-conventions)
3. [Prerequisites](#3-prerequisites)
4. [Project Structure](#4-project-structure)
5. [Local Development Setup](#5-local-development-setup)
6. [Backend Implementation](#6-backend-implementation)
7. [Frontend Implementation](#7-frontend-implementation)
8. [Neon PostgreSQL Setup](#8-neon-postgresql-setup)
9. [Azure Deployment](#9-azure-deployment)
10. [GitHub Actions CI/CD](#10-github-actions-cicd)
11. [Environment Variables Guide](#11-environment-variables-guide)
12. [Common Pitfalls & Solutions](#12-common-pitfalls--solutions)
13. [Deployment Checklist](#13-deployment-checklist)
14. [Quick Reference Commands](#14-quick-reference-commands)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              GitHub Repository                                │
│                                                                              │
│  ┌─────────────────────────┐              ┌─────────────────────────────┐   │
│  │ .github/workflows/      │              │ .github/workflows/          │   │
│  │ deploy-frontend.yml     │              │ deploy-backend.yml          │   │
│  └───────────┬─────────────┘              └──────────────┬──────────────┘   │
└──────────────┼───────────────────────────────────────────┼──────────────────┘
               │                                           │
               ▼                                           ▼
┌──────────────────────────────┐        ┌──────────────────────────────────────┐
│   Azure Static Web Apps      │        │       Azure App Service              │
│   ────────────────────────   │        │       ──────────────────             │
│   • Vite + TypeScript        │───────▶│       • FastAPI + Python 3.12        │
│   • Global CDN               │  API   │       • Gunicorn + Uvicorn           │
│   • HTTPS automatic          │ Calls  │       • Connection pooling           │
│   • Free tier available      │        │       • Retry logic                  │
└──────────────────────────────┘        └───────────────┬──────────────────────┘
                                                        │
                                                        │ DATABASE_URL
                                                        ▼
                                        ┌──────────────────────────────────────┐
                                        │       Neon PostgreSQL                │
                                        │       ────────────────               │
                                        │       • Serverless (scales to zero)  │
                                        │       • Free tier: 0.5GB storage     │
                                        │       • Cold start: 5-10s            │
                                        │       • Connection pooling built-in  │
                                        └──────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Vite 7.x + Bun | Build tool + runtime |
| **Frontend** | TypeScript 5.x | Type safety |
| **Backend** | FastAPI 0.128+ | Python web framework |
| **Backend** | SQLAlchemy 2.x | ORM |
| **Backend** | Gunicorn + Uvicorn | ASGI server |
| **Database (Local)** | SQLite | Zero-config dev |
| **Database (Prod)** | Neon PostgreSQL | Serverless PostgreSQL |
| **Hosting (Frontend)** | Azure Static Web Apps | CDN + HTTPS |
| **Hosting (Backend)** | Azure App Service | Python runtime |
| **CI/CD** | GitHub Actions | Automated deployment |

---

## 2. Naming Conventions

### 🏷️ Consistent Naming Pattern

Use a **consistent project slug** across all resources:

```
Project Name: "Task Tracker"
Project Slug: "task-tracker"
```

| Resource Type | Naming Pattern | Example |
|---------------|----------------|---------|
| **Resource Group** | `{slug}-rg` | `task-tracker-rg` |
| **App Service Plan** | `{slug}-plan` | `task-tracker-plan` |
| **Backend Web App** | `{slug}-api` | `task-tracker-api` |
| **Static Web App** | `{slug}-web` | `task-tracker-web` |
| **Neon Project** | `{slug}` | `task-tracker` |
| **Neon Database** | `{slug}_db` or `neondb` | `task_tracker_db` |
| **GitHub Repo** | `{slug}` | `task-tracker` |

### 📁 File Naming

```
backend/
├── application.py          # Main app (NOT main.py - Azure quirk!)
├── pyproject.toml          # Dependencies
├── requirements.txt        # Generated - DO NOT EDIT
└── .env.example            # Template for local dev

frontend/
├── src/
│   ├── main.ts
│   └── api.ts              # API client
├── .env.development        # Local API URL
├── .env.production         # Prod API URL (template)
└── .env.example            # Template
```

---

## 3. Prerequisites

### Install Required Tools

```bash
# macOS with Homebrew
brew install bun             # Frontend runtime
brew install uv              # Python package manager (Astral)
brew install python@3.12     # Python runtime
brew install azure-cli       # Azure CLI
brew install gh              # GitHub CLI
brew install neonctl         # Neon CLI

# Verify installations
bun --version                # >= 1.0
uv --version                 # >= 0.1
python3 --version            # >= 3.12
az --version                 # >= 2.50
gh --version                 # >= 2.0
neonctl --version            # >= 1.0
```

### Authenticate CLIs

```bash
# Azure (opens browser)
az login

# GitHub (opens browser)
gh auth login

# Neon (opens browser)
neonctl auth
```

---

## 4. Project Structure

### Create Project Scaffold

```bash
# Set your project name
PROJECT_NAME="task-tracker"

# Create directories
mkdir -p $PROJECT_NAME/{frontend,backend,docs,.github/workflows}
cd $PROJECT_NAME

# Initialize git
git init
echo "# $PROJECT_NAME" > README.md
```

### Final Structure

```
task-tracker/
├── frontend/
│   ├── src/
│   │   ├── main.ts              # Entry point
│   │   ├── api.ts               # API client
│   │   ├── types.ts             # TypeScript types
│   │   └── style.css            # Styles
│   ├── public/
│   │   └── favicon.ico
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env.development         # Local: VITE_API_URL=http://localhost:8000
│   ├── .env.production          # Prod: VITE_API_URL=https://xxx-api.azurewebsites.net
│   └── .env.example             # Template for others
├── backend/
│   ├── application.py           # ⚠️ MUST be application.py, NOT main.py
│   ├── pyproject.toml
│   ├── requirements.txt         # Generated with: uv pip compile
│   ├── .env                     # Local dev (gitignored)
│   └── .env.example             # Template
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml
│       └── deploy-backend.yml
├── docs/
│   └── DEPLOYMENT_GUIDE.md
├── .gitignore
├── AGENTS.md                    # AI agent guidelines
└── README.md
```

### Essential .gitignore

```bash
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
.venv/
__pycache__/

# Build outputs
dist/
build/
*.egg-info/

# Environment files (contain secrets!)
.env
.env.local
.env.*.local
!.env.example
!.env.development
!.env.production

# Database files
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Azure
.azure/
EOF
```

---

## 5. Local Development Setup

### Backend: Python with uv

```bash
cd backend

# Initialize Python project
uv init --name backend

# Add dependencies
uv add fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv

# Create virtual environment
uv venv
source .venv/bin/activate  # or: .venv/Scripts/activate on Windows

# Generate requirements.txt (REQUIRED for Azure!)
uv pip compile pyproject.toml -o requirements.txt
```

### Frontend: Vite with Bun

```bash
cd frontend

# Create Vite project
bun create vite . --template vanilla-ts

# Install dependencies
bun install
```

### Local Environment Files

**backend/.env** (gitignored - contains secrets):
```bash
# Local development - SQLite (zero config)
DATABASE_URL=sqlite:///./dev.db

# OR: Local PostgreSQL via Docker
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/task_tracker_dev
```

**backend/.env.example** (committed - template):
```bash
# Database connection
# Local: sqlite:///./dev.db
# Docker: postgresql://postgres:postgres@localhost:5432/myapp_dev
# Neon: postgresql://user:pass@host/dbname?sslmode=require
DATABASE_URL=sqlite:///./dev.db

# Optional
DEBUG=true
```

**frontend/.env.development** (committed - no secrets):
```bash
VITE_API_URL=http://localhost:8000
```

**frontend/.env.production** (committed - template, actual value in CI):
```bash
# Set via GitHub Variables in CI/CD
# VITE_API_URL=https://your-app-api.azurewebsites.net
VITE_API_URL=
```

**frontend/.env.example** (committed - template):
```bash
# Backend API URL
# Local: http://localhost:8000
# Production: https://your-app-api.azurewebsites.net
VITE_API_URL=http://localhost:8000
```

---

## 6. Backend Implementation

### application.py (MUST be this filename!)

```python
"""
FastAPI Backend with SQLite (dev) / PostgreSQL (prod) support.

⚠️ CRITICAL: File MUST be named 'application.py' for Azure Oryx auto-detection!
   If named 'main.py', Azure won't find it and will serve default page.
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

# Load environment variables from .env file (local dev)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
logger.info(f"Database: {DATABASE_URL.split('://')[0]}")

# Connection configuration based on database type
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL (Neon) configuration
    # Neon serverless can have 5-15s cold starts on free tier!
    engine_kwargs = {
        "poolclass": QueuePool,
        "pool_size": 2,           # Min connections
        "max_overflow": 3,        # Extra connections if needed
        "pool_timeout": 60,       # Wait up to 60s for connection (cold start)
        "pool_pre_ping": True,    # Verify connections are alive
        "pool_recycle": 300,      # Recycle connections every 5 min
    }
    connect_args = {"connect_timeout": 60}  # Connection timeout for cold start

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# MODELS
# ============================================================================

class User(Base):
    """Example User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)  # Explicit length for PostgreSQL
    email = Column(String(255), unique=True, index=True)


# ============================================================================
# DATABASE INITIALIZATION WITH RETRY LOGIC
# ============================================================================

def init_database() -> bool:
    """
    Initialize database tables with retry logic for Neon cold starts.
    
    Returns:
        bool: True if successful, False otherwise
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Database init attempt {attempt + 1}/{max_retries}")
            Base.metadata.create_all(bind=engine)
            logger.info("✓ Database tables created successfully")
            return True
        except Exception as e:
            logger.warning(f"Database init failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
    logger.error("✗ Database initialization failed after all retries")
    return False


def seed_database():
    """
    Seed database with initial data.
    
    Handles race conditions when multiple workers start simultaneously.
    Uses check-then-insert pattern with exception handling.
    """
    max_retries = 3
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            # Check if already seeded
            existing_count = db.query(User).count()
            if existing_count > 0:
                logger.info(f"✓ Database already has {existing_count} users, skipping seed")
                return
            
            # Seed initial data
            users = [
                User(name="Alice Johnson", email="alice@example.com"),
                User(name="Bob Smith", email="bob@example.com"),
                User(name="Charlie Brown", email="charlie@example.com"),
                User(name="Diana Prince", email="diana@example.com"),
                User(name="Eve Wilson", email="eve@example.com"),
            ]
            db.add_all(users)
            db.commit()
            logger.info(f"✓ Database seeded with {len(users)} users")
            return
            
        except Exception as e:
            db.rollback()
            logger.warning(f"Seed attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
        finally:
            db.close()
    
    logger.error("✗ Database seeding failed after all retries")


# ============================================================================
# FASTAPI APP LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    # Startup
    logger.info("🚀 Application starting up...")
    if init_database():
        seed_database()
    else:
        logger.error("⚠️ Database init failed - app may not work correctly")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("👋 Application shutting down...")


# ============================================================================
# FASTAPI APP CONFIGURATION
# ============================================================================

app = FastAPI(
    title="Task Tracker API",
    description="A simple API for task tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# In production, replace "*" with your actual frontend URL
ALLOWED_ORIGINS = [
    "http://localhost:5173",           # Vite dev server
    "http://localhost:3000",           # Alternative local port
    "https://*.azurestaticapps.net",   # Azure Static Web Apps
]

# Add your production frontend URL
FRONTEND_URL = os.environ.get("FRONTEND_URL")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# API ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Task Tracker API",
        "status": "healthy",
        "database": DATABASE_URL.split("://")[0],
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {"status": "healthy"}


@app.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """Get all users."""
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


@app.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}


@app.post("/users")
async def create_user(name: str, email: str, db: Session = Depends(get_db)):
    """Create a new user."""
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email}


# ============================================================================
# LOCAL DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("application:app", host="0.0.0.0", port=8000, reload=True)
```

### pyproject.toml

```toml
[project]
name = "backend"
version = "0.1.0"
description = "FastAPI backend with PostgreSQL"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "gunicorn>=23.0.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.9",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Generate requirements.txt (CRITICAL!)

```bash
cd backend
uv pip compile pyproject.toml -o requirements.txt
```

⚠️ **Azure App Service uses `requirements.txt`, NOT `pyproject.toml`!**

---

## 7. Frontend Implementation

### src/api.ts - API Client

```typescript
/**
 * API Client for backend communication.
 * 
 * Uses VITE_API_URL environment variable.
 * Falls back to localhost for development.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface ApiStatus {
  message: string;
  status: string;
  database: string;
}

/**
 * Fetch with error handling and timeout.
 */
async function fetchWithTimeout(
  url: string, 
  options: RequestInit = {}, 
  timeout = 30000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Get API status.
 */
export async function getApiStatus(): Promise<ApiStatus> {
  const response = await fetchWithTimeout(`${API_URL}/`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * Get all users.
 */
export async function getUsers(): Promise<User[]> {
  const response = await fetchWithTimeout(`${API_URL}/users`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * Get user by ID.
 */
export async function getUser(id: number): Promise<User> {
  const response = await fetchWithTimeout(`${API_URL}/users/${id}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}
```

### src/main.ts - Entry Point

```typescript
import './style.css';
import { getApiStatus, getUsers, User, ApiStatus } from './api';

const app = document.querySelector<HTMLDivElement>('#app')!;

async function renderApp() {
  app.innerHTML = `
    <div class="container">
      <h1>Task Tracker</h1>
      <div id="status">Loading...</div>
      <div id="users">Loading users...</div>
    </div>
  `;

  const statusEl = document.querySelector<HTMLDivElement>('#status')!;
  const usersEl = document.querySelector<HTMLDivElement>('#users')!;

  try {
    // Fetch API status
    const status: ApiStatus = await getApiStatus();
    statusEl.innerHTML = `
      <p class="success">✓ API: ${status.status}</p>
      <p>Database: ${status.database}</p>
    `;

    // Fetch users
    const users: User[] = await getUsers();
    usersEl.innerHTML = `
      <h2>Users (${users.length})</h2>
      <ul>
        ${users.map(u => `<li>${u.name} (${u.email})</li>`).join('')}
      </ul>
    `;
  } catch (error) {
    statusEl.innerHTML = `<p class="error">✗ API Error: ${error}</p>`;
    usersEl.innerHTML = '';
  }
}

renderApp();
```

### vite.config.ts

```typescript
import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    // Proxy API calls in development (optional alternative to CORS)
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

---

## 8. Neon PostgreSQL Setup

### Create Neon Project

```bash
# Set project name (use your project slug)
PROJECT_SLUG="task-tracker"

# Create Neon project
neonctl projects create --name $PROJECT_SLUG --region-id aws-us-east-1

# Get project ID
PROJECT_ID=$(neonctl projects list --output json | jq -r ".[] | select(.name==\"$PROJECT_SLUG\") | .id")
echo "Project ID: $PROJECT_ID"

# Get connection string
CONNECTION_STRING=$(neonctl connection-string --project-id $PROJECT_ID)
echo "Connection String: $CONNECTION_STRING"
```

### Alternative: Use Neon Console

1. Go to https://console.neon.tech
2. Click "New Project"
3. Name: `task-tracker` (your project slug)
4. Region: `aws-us-east-1` (or closest to Azure region)
5. Copy connection string from Dashboard

### Connection String Format

```
postgresql://USER:PASSWORD@ENDPOINT.REGION.aws.neon.tech/neondb?sslmode=require
```

Example:
```
postgresql://neondb_owner:abc123xyz@ep-cool-wind-12345.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### ⚠️ Neon Free Tier Limitations

| Limit | Value | Impact |
|-------|-------|--------|
| Compute hours | 100/month | ~3 hours/day active |
| Storage | 0.5 GB | Plan data carefully |
| Cold start | 5-15 seconds | Need timeout handling |
| Connections | 100 pooled | Use connection pooling |

---

## 9. Azure Deployment

### Step 1: Set Variables

```bash
# Project configuration
PROJECT_SLUG="task-tracker"
LOCATION="centralus"              # Check quota! Alternative: eastus, westus2
RESOURCE_GROUP="${PROJECT_SLUG}-rg"
PLAN_NAME="${PROJECT_SLUG}-plan"
BACKEND_NAME="${PROJECT_SLUG}-api"
FRONTEND_NAME="${PROJECT_SLUG}-web"

# Database (from Neon)
DATABASE_URL="postgresql://user:pass@endpoint.neon.tech/neondb?sslmode=require"
```

### Step 2: Create Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 3: Create App Service Plan

```bash
# B1 = Basic tier (~$13/month)
# F1 = Free tier (limited, often no quota)
az appservice plan create \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1 \
  --is-linux
```

### Step 4: Create Backend Web App

```bash
# Create the web app
az webapp create \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $PLAN_NAME \
  --runtime "PYTHON:3.12"

# ⚠️ CRITICAL: Set startup command
# - Must use 'application:app' (not main:app)
# - Use single worker for SQLite, can use more for PostgreSQL
# - Timeout 120s to handle Neon cold starts
az webapp config set \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "gunicorn application:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120"

# Set DATABASE_URL environment variable
az webapp config appsettings set \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings DATABASE_URL="$DATABASE_URL"

# Enable build during deployment
az webapp config appsettings set \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Enable logging
az webapp log config \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --application-logging filesystem \
  --level verbose \
  --detailed-error-messages true
```

### Step 5: Deploy Backend

```bash
cd backend

# Deploy using az webapp up (simplest method)
az webapp up \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --runtime "PYTHON:3.12" \
  --sku B1

# Verify deployment
curl https://${BACKEND_NAME}.azurewebsites.net/
# Should return: {"message":"Task Tracker API","status":"healthy",...}

curl https://${BACKEND_NAME}.azurewebsites.net/users
# Should return: [{"id":1,"name":"Alice Johnson",...},...]
```

### Step 6: Create Static Web App (Frontend)

```bash
# Create SWA (free tier)
az staticwebapp create \
  --name $FRONTEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --location "eastus2" \
  --sku Free

# Get deployment token (save this!)
SWA_TOKEN=$(az staticwebapp secrets list \
  --name $FRONTEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.apiKey" -o tsv)

echo "SWA Token: $SWA_TOKEN"
```

### Step 7: Configure Frontend Environment

```bash
# Set API URL in GitHub Variables (for CI/CD)
BACKEND_URL="https://${BACKEND_NAME}.azurewebsites.net"
gh variable set VITE_API_URL --body "$BACKEND_URL"

# Store SWA token as secret
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body "$SWA_TOKEN"
```

---

## 10. GitHub Actions CI/CD

### Backend Workflow (.github/workflows/deploy-backend.yml)

```yaml
name: Deploy Backend

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - '.github/workflows/deploy-backend.yml'
  workflow_dispatch:

jobs:
  deploy:
    # ⚠️ Must include workflow_dispatch in condition!
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Deploy to Azure
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ vars.AZURE_BACKEND_NAME }}
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: './backend'
```

### Frontend Workflow (.github/workflows/deploy-frontend.yml)

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy-frontend.yml'
  workflow_dispatch:

jobs:
  deploy:
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Bun
        uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest
      
      - name: Install dependencies
        run: cd frontend && bun install
      
      - name: Build
        run: cd frontend && bun run build
        env:
          VITE_API_URL: ${{ vars.VITE_API_URL }}
      
      - name: Deploy to Azure SWA
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "frontend"
          output_location: "dist"
          skip_app_build: true  # We already built it
```

### Setup GitHub Secrets & Variables

```bash
# Get App Service publish profile
az webapp deployment list-publishing-profiles \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --xml > /tmp/publish_profile.xml

# Set secrets
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < /tmp/publish_profile.xml
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body "$SWA_TOKEN"

# Set variables
gh variable set AZURE_BACKEND_NAME --body "$BACKEND_NAME"
gh variable set VITE_API_URL --body "https://${BACKEND_NAME}.azurewebsites.net"

# Clean up
rm /tmp/publish_profile.xml
```

---

## 11. Environment Variables Guide

### Backend Environment Variables

| Variable | Local | Production | Required |
|----------|-------|------------|----------|
| `DATABASE_URL` | `sqlite:///./dev.db` | `postgresql://...neon.tech/...` | ✅ Yes |
| `DEBUG` | `true` | `false` | ❌ No |
| `FRONTEND_URL` | - | `https://xxx.azurestaticapps.net` | ❌ No |

**How to set in Azure:**
```bash
az webapp config appsettings set \
  --name $BACKEND_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    DATABASE_URL="postgresql://..." \
    DEBUG="false" \
    FRONTEND_URL="https://..."
```

### Frontend Environment Variables

| Variable | Local | Production | Required |
|----------|-------|------------|----------|
| `VITE_API_URL` | `http://localhost:8000` | `https://xxx-api.azurewebsites.net` | ✅ Yes |

⚠️ **MUST use `VITE_` prefix** for client-side variables!

**How to set for builds:**
```bash
# GitHub Variables (used in CI/CD)
gh variable set VITE_API_URL --body "https://xxx-api.azurewebsites.net"
```

### Reading Environment Variables

**Backend (Python):**
```python
import os
from dotenv import load_dotenv

# Load .env file (local dev only)
load_dotenv()

# Read variable
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
```

**Frontend (TypeScript):**
```typescript
// Vite injects VITE_* variables at build time
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

---

## 12. Common Pitfalls & Solutions

### ❌ Pitfall 1: File named `main.py` instead of `application.py`

**Symptom:** Azure shows "Hey, Python developers! Your app service is up..." default page.

**Why:** Azure Oryx auto-detection looks for `application.py` or `app.py`, NOT `main.py`.

**Solution:**
```bash
# Rename the file
mv backend/main.py backend/application.py

# Update startup command
az webapp config set --startup-file "gunicorn application:app ..."
```

---

### ❌ Pitfall 2: Missing `requirements.txt`

**Symptom:** `ModuleNotFoundError: No module named 'fastapi'`

**Why:** Azure uses `requirements.txt`, not `pyproject.toml`.

**Solution:**
```bash
cd backend
uv pip compile pyproject.toml -o requirements.txt
git add requirements.txt && git commit -m "Add requirements.txt"
```

---

### ❌ Pitfall 3: Neon cold start timeout

**Symptom:** Container exits with code 1, "startup probe failed"

**Why:** Neon free tier can take 5-15s to wake from sleep. Default timeouts are too short.

**Solution:**
```python
# In application.py - increase timeouts
engine_kwargs = {
    "pool_timeout": 60,      # Wait 60s for connection
}
connect_args = {"connect_timeout": 60}
```

```bash
# In startup command - increase worker timeout
az webapp config set --startup-file "gunicorn application:app --timeout 120 ..."
```

---

### ❌ Pitfall 4: SQLite race condition with multiple workers

**Symptom:** `sqlite3.IntegrityError: UNIQUE constraint failed`

**Why:** Multiple Gunicorn workers try to seed database simultaneously.

**Solution:**
```bash
# Use single worker for SQLite
az webapp config set --startup-file "gunicorn application:app --workers 1 ..."
```

Or use PostgreSQL (Neon) which handles concurrent connections properly.

---

### ❌ Pitfall 5: PostgreSQL String column needs explicit length

**Symptom:** `sqlalchemy.exc.CompileError: VARCHAR requires a length`

**Why:** SQLite allows `String()` without length, PostgreSQL doesn't.

**Solution:**
```python
# Always specify length for String columns
name = Column(String(100), index=True)      # ✅ Works
email = Column(String(255), unique=True)    # ✅ Works
# name = Column(String, index=True)         # ❌ Fails on PostgreSQL
```

---

### ❌ Pitfall 6: Workflow skipped on manual trigger

**Symptom:** Workflow shows "skipped" when using workflow_dispatch.

**Why:** Job `if` condition doesn't include `workflow_dispatch`.

**Solution:**
```yaml
# ❌ Wrong
if: github.event_name == 'push'

# ✅ Correct
if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
```

---

### ❌ Pitfall 7: CORS errors

**Symptom:** `Access to fetch blocked by CORS policy`

**Solution:**
```python
# In application.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-swa.azurestaticapps.net"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### ❌ Pitfall 8: Azure quota exceeded

**Symptom:** `QuotaExceeded: This region has quota of 0 instances`

**Solution:** Try different regions:
```bash
# Usually have quota
--location "centralus"
--location "eastus"
--location "westus2"
--location "westeurope"
```

---

### ❌ Pitfall 9: Environment variable not available in frontend

**Symptom:** `import.meta.env.API_URL` is undefined

**Why:** Only `VITE_` prefixed variables are exposed to client.

**Solution:**
```typescript
// ❌ Won't work
const url = import.meta.env.API_URL

// ✅ Works
const url = import.meta.env.VITE_API_URL
```

---

### ❌ Pitfall 10: Startup command not being used

**Symptom:** Logs show "App Command Line not configured, will attempt auto-detect"

**Why:** Need to redeploy after setting startup command.

**Solution:**
```bash
# Set startup command
az webapp config set --startup-file "gunicorn application:app ..."

# Then redeploy
cd backend && az webapp up --name $BACKEND_NAME --runtime "PYTHON:3.12"
```

---

### ❌ Pitfall 11: Publish profile is invalid (GitHub Actions deployment)

**Symptom:** `Deployment Failed, Error: Publish profile is invalid for app-name and slot-name provided`

**Why:** Basic Authentication is disabled on the Azure App Service. The `azure/webapps-deploy` action uses Basic Auth with publish profile credentials.

**Solution:**
```bash
# Check if Basic Auth is disabled
az rest --method get --uri "https://management.azure.com/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{app}/basicPublishingCredentialsPolicies?api-version=2022-03-01"

# Enable Basic Auth for SCM (deployment)
az rest --method put \
  --uri "https://management.azure.com/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{app}/basicPublishingCredentialsPolicies/scm?api-version=2022-03-01" \
  --body '{"properties":{"allow":true}}'

# Enable Basic Auth for FTP (optional)
az rest --method put \
  --uri "https://management.azure.com/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{app}/basicPublishingCredentialsPolicies/ftp?api-version=2022-03-01" \
  --body '{"properties":{"allow":true}}'

# Get fresh publish profile and update GitHub secret
az webapp deployment list-publishing-profiles --name {app} --resource-group {rg} --xml > publish_profile.xml
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < publish_profile.xml
```

---

### ❌ Pitfall 12: Stale publish profile after app recreation

**Symptom:** Same as Pitfall 11 - "Publish profile is invalid"

**Why:** If you delete and recreate the App Service, the old publish profile stored in GitHub secrets becomes invalid.

**Solution:**
```bash
# Get fresh publish profile from Azure
az webapp deployment list-publishing-profiles \
  --name YOUR_APP_NAME \
  --resource-group YOUR_RG_NAME \
  --xml > /tmp/publish_profile.xml

# Update GitHub secret
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE --repo YOUR_REPO < /tmp/publish_profile.xml

# Trigger workflow again
gh workflow run deploy-backend.yml --repo YOUR_REPO
```

---

## 13. Deployment Checklist

### ✅ Pre-Deployment

- [ ] `application.py` (NOT `main.py`)
- [ ] `requirements.txt` generated from `pyproject.toml`
- [ ] String columns have explicit length: `String(100)`
- [ ] Connection pooling and timeouts for Neon
- [ ] Retry logic in database initialization
- [ ] CORS middleware configured
- [ ] `.env.example` files created
- [ ] `.gitignore` excludes `.env` files

### ✅ Neon Setup

- [ ] Neon project created with clean name
- [ ] Connection string saved securely
- [ ] Free tier limits understood (100 compute hours/month)

### ✅ Azure Setup

- [ ] Resource group created
- [ ] App Service Plan created (check region quota!)
- [ ] Backend Web App created
- [ ] **Startup command set with correct filename**
- [ ] DATABASE_URL environment variable set
- [ ] SCM_DO_BUILD_DURING_DEPLOYMENT=true
- [ ] Logging enabled
- [ ] Static Web App created
- [ ] CORS configured

### ✅ GitHub Setup

- [ ] `AZURE_STATIC_WEB_APPS_API_TOKEN` secret set
- [ ] `AZURE_WEBAPP_PUBLISH_PROFILE` secret set
- [ ] `VITE_API_URL` variable set
- [ ] `AZURE_BACKEND_NAME` variable set
- [ ] Workflows include `workflow_dispatch` in conditions

### ✅ Post-Deployment Verification

- [ ] Backend `/` returns JSON response
- [ ] Backend `/users` returns seeded data
- [ ] Frontend loads correctly
- [ ] Frontend can fetch from backend
- [ ] No CORS errors in browser console
- [ ] Check logs for any errors

---

## 14. Quick Reference Commands

### Local Development

```bash
# Backend
cd backend
source .venv/bin/activate    # Activate venv
uv run uvicorn application:app --reload --port 8000

# Frontend
cd frontend
bun run dev

# Regenerate requirements.txt
cd backend && uv pip compile pyproject.toml -o requirements.txt
```

### Azure Deployment

```bash
# Deploy backend
cd backend && az webapp up --name $BACKEND_NAME --runtime "PYTHON:3.12"

# Deploy frontend (triggers CI/CD)
git push origin main

# Manual frontend workflow trigger
gh workflow run deploy-frontend.yml
```

### Monitoring & Debugging

```bash
# Stream backend logs
az webapp log tail --name $BACKEND_NAME --resource-group $RESOURCE_GROUP

# Download logs for analysis
az webapp log download --name $BACKEND_NAME --resource-group $RESOURCE_GROUP --log-file logs.zip

# Restart backend
az webapp restart --name $BACKEND_NAME --resource-group $RESOURCE_GROUP

# Check app settings
az webapp config appsettings list --name $BACKEND_NAME --resource-group $RESOURCE_GROUP
```

### Neon Database

```bash
# List projects
neonctl projects list

# Get connection string
neonctl connection-string --project-id $PROJECT_ID

# Connect with psql
psql "$(neonctl connection-string --project-id $PROJECT_ID)"
```

### Cleanup

```bash
# Delete everything
az group delete --name $RESOURCE_GROUP --yes --no-wait

# Delete Neon project
neonctl projects delete $PROJECT_ID
```

---

## Summary: Key Differences from Standard Tutorials

| Standard Tutorial | This Guide (Battle-Tested) |
|-------------------|----------------------------|
| `main.py` | `application.py` (Azure quirk) |
| `pip install` | `uv` + `requirements.txt` |
| No timeout handling | 60s+ timeouts for Neon cold starts |
| Simple db init | Retry logic with exponential backoff |
| `--workers 4` | `--workers 1` for SQLite safety |
| `String` | `String(100)` explicit length |
| `if: push` | `if: push \|\| workflow_dispatch` |

---

*Last updated: January 2026*
*Tested with: Vite 7.x, Bun 1.x, FastAPI 0.128+, Python 3.12, Neon PostgreSQL*
