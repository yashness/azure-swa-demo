# Azure Deployment Guide: Frontend + Backend with SQLite

A comprehensive guide for deploying Vite/Bun frontend to Azure Static Web Apps and FastAPI/Python backend with SQLite to Azure App Service.

> **Based on real deployment experience** - This guide documents actual issues encountered and their solutions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Backend Setup (FastAPI + SQLite)](#backend-setup-fastapi--sqlite)
5. [Frontend Setup (Vite + Bun)](#frontend-setup-vite--bun)
6. [Azure Resource Provisioning](#azure-resource-provisioning)
7. [GitHub Actions Workflows](#github-actions-workflows)
8. [Common Issues & Solutions](#common-issues--solutions)
9. [Deployment Checklist](#deployment-checklist)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                        │
│  ┌─────────────────────┐         ┌─────────────────────────────┐│
│  │  .github/workflows/ │         │  .github/workflows/         ││
│  │  deploy-frontend.yml│         │  deploy-backend.yml         ││
│  └──────────┬──────────┘         └──────────────┬──────────────┘│
└─────────────┼───────────────────────────────────┼───────────────┘
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐       ┌─────────────────────────────┐
│  Azure Static Web Apps  │       │    Azure App Service        │
│  ─────────────────────  │       │    ───────────────────      │
│  • Vite/Bun frontend    │──────▶│    • FastAPI backend        │
│  • Global CDN           │ CORS  │    • SQLite database        │
│  • Free tier available  │       │    • Linux Python runtime   │
└─────────────────────────┘       └─────────────────────────────┘
```

---

## Prerequisites

### Local Development Tools
- **Bun** (frontend package manager & runtime)
- **Python 3.11+** (backend runtime)
- **uv** (Python package manager by Astral)
- **Azure CLI** (`az`)
- **GitHub CLI** (`gh`)

### Azure Requirements
- Azure subscription with active quota
- Sufficient quota for App Service Plan in your region

---

## Project Structure

```
project-root/
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── backend/
│   ├── main.py
│   ├── pyproject.toml
│   └── requirements.txt        # Generated from pyproject.toml
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml
│       └── deploy-backend.yml
├── docs/
│   └── AZURE_DEPLOYMENT_GUIDE.md
└── README.md
```

---

## Backend Setup (FastAPI + SQLite)

### Critical: SQLite + Gunicorn Race Condition

**⚠️ THE MOST IMPORTANT LESSON FROM THIS DEPLOYMENT**

When using SQLite with Gunicorn (multiple workers), you **will** encounter race conditions during database initialization:

```
sqlite3.IntegrityError: UNIQUE constraint failed: users.email
```

**Why it happens:**
1. Gunicorn spawns multiple workers (default: 2-4)
2. Each worker runs your `startup` event simultaneously
3. All workers try to create/seed the database at the same time
4. SQLite doesn't handle concurrent writes well → crashes

### Solution 1: Single Worker (Recommended for SQLite)

```bash
# Startup command for Azure App Service
gunicorn main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Solution 2: Exception Handling (Defense in Depth)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    # Shutdown (cleanup if needed)

def seed_database():
    """Seed with exception handling for race conditions."""
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).first():
            return
        
        users = [
            User(name="Alice", email="alice@example.com"),
            User(name="Bob", email="bob@example.com"),
        ]
        db.add_all(users)
        db.commit()
    except Exception as e:
        db.rollback()
        # Log but don't crash - another worker likely seeded already
        print(f"Seed skipped (likely already done): {e}")
    finally:
        db.close()

app = FastAPI(lifespan=lifespan)
```

### Solution 3: Use PostgreSQL for Production

For production apps with multiple workers, use PostgreSQL:
- Azure Database for PostgreSQL
- Handles concurrent connections properly
- Better for scaling

### Backend Requirements File

**Always generate `requirements.txt` from `pyproject.toml`:**

```bash
cd backend
uv pip compile pyproject.toml -o requirements.txt
```

Azure App Service uses `requirements.txt` during deployment, not `pyproject.toml`.

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",           # Local dev
        "https://*.azurestaticapps.net",   # Azure SWA
        "https://your-custom-domain.com",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Frontend Setup (Vite + Bun)

### Environment Variables

Create `.env` files for different environments:

```bash
# .env.development
VITE_API_URL=http://localhost:8000

# .env.production (or set via GitHub Variables)
VITE_API_URL=https://your-backend.azurewebsites.net
```

### Accessing Environment Variables

```typescript
// In your TypeScript code
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function fetchData() {
  const response = await fetch(`${API_URL}/endpoint`)
  return response.json()
}
```

### Vite Config for API Proxy (Development)

```typescript
// vite.config.ts
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

---

## Azure Resource Provisioning

### Step 1: Create Resource Group

```bash
RESOURCE_GROUP="my-app-rg"
LOCATION="centralus"  # Check quota availability!

az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 2: Create Static Web App (Frontend)

```bash
SWA_NAME="my-app-frontend"

az staticwebapp create \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --location "eastus2" \
  --sku Free
```

Get the deployment token:
```bash
az staticwebapp secrets list \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.apiKey" -o tsv
```

### Step 3: Create App Service (Backend)

```bash
PLAN_NAME="my-app-plan"
WEBAPP_NAME="my-app-api"

# Create App Service Plan
az appservice plan create \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $PLAN_NAME \
  --runtime "PYTHON:3.12"

# ⚠️ CRITICAL: Set startup command with SINGLE WORKER for SQLite
az webapp config set \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "gunicorn main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
```

### Step 4: Configure CORS on Backend

```bash
az webapp cors add \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "https://your-swa-url.azurestaticapps.net"
```

---

## GitHub Actions Workflows

### Frontend Workflow (deploy-frontend.yml)

```yaml
name: Deploy Frontend to Azure SWA

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy-frontend.yml'
  workflow_dispatch:

jobs:
  build_and_deploy:
    # ⚠️ Include workflow_dispatch in condition!
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
          skip_app_build: true
```

### Backend Workflow (deploy-backend.yml)

```yaml
name: Deploy Backend to Azure App Service

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - '.github/workflows/deploy-backend.yml'
  workflow_dispatch:

jobs:
  build_and_deploy:
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
      
      - name: Deploy to Azure App Service
        uses: azure/webapps-deploy@v3
        with:
          app-name: 'your-app-name'
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: './backend'
```

### GitHub Secrets & Variables Setup

```bash
# Get SWA deployment token
SWA_TOKEN=$(az staticwebapp secrets list --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "properties.apiKey" -o tsv)
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body "$SWA_TOKEN"

# Get App Service publish profile
az webapp deployment list-publishing-profiles \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --xml > publish_profile.xml
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < publish_profile.xml
rm publish_profile.xml

# Set frontend API URL variable
gh variable set VITE_API_URL --body "https://$WEBAPP_NAME.azurewebsites.net"
```

---

## Common Issues & Solutions

### Issue 1: SQLite Race Condition (CRITICAL)

**Error:**
```
sqlite3.IntegrityError: UNIQUE constraint failed
Container exit code: 1 or 3
```

**Cause:** Multiple Gunicorn workers trying to seed database simultaneously.

**Solution:**
```bash
# Use single worker
az webapp config set --startup-file "gunicorn main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
```

---

### Issue 2: ModuleNotFoundError

**Error:**
```
ModuleNotFoundError: No module named 'uvicorn'
```

**Cause:** Dependencies not installing during deployment.

**Solutions:**

1. **Ensure `requirements.txt` exists:**
   ```bash
   cd backend && uv pip compile pyproject.toml -o requirements.txt
   ```

2. **Enable SCM build during deployment:**
   ```bash
   az webapp config appsettings set \
     --name $WEBAPP_NAME \
     --resource-group $RESOURCE_GROUP \
     --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
   ```

3. **Use `az webapp up` for simple deployments:**
   ```bash
   cd backend && az webapp up --name $WEBAPP_NAME --runtime "PYTHON:3.12"
   ```

---

### Issue 3: Azure Quota Limits

**Error:**
```
Code: QuotaExceeded
This region has quota of 0 instances for your subscription
```

**Cause:** Your subscription has no quota in the selected region.

**Solution:** Try different regions:
```bash
# Common regions with good availability
az appservice plan create --location "centralus" ...    # Usually available
az appservice plan create --location "eastus2" ...      # Alternative
az appservice plan create --location "westeurope" ...   # Europe
```

---

### Issue 4: Workflow Skipped on Manual Trigger

**Error:** Workflow shows "skipped" when using `workflow_dispatch`.

**Cause:** Job `if` condition doesn't include `workflow_dispatch`.

**Wrong:**
```yaml
if: github.event_name == 'push'
```

**Correct:**
```yaml
if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
```

---

### Issue 5: CORS Errors

**Error:**
```
Access to fetch blocked by CORS policy
```

**Solutions:**

1. **Add CORS middleware in FastAPI:**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-swa.azurestaticapps.net"],
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Configure CORS in Azure:**
   ```bash
   az webapp cors add --allowed-origins "https://your-swa.azurestaticapps.net"
   ```

---

### Issue 6: Container Keeps Restarting

**Error:** Logs show container exit code 1/3 repeatedly.

**Debugging:**
```bash
# Stream live logs
az webapp log tail --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP

# Check specific error logs
az webapp log download --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

**Common causes:**
- Missing dependencies (check requirements.txt)
- SQLite race condition (use single worker)
- Port binding issue (ensure `--bind 0.0.0.0:8000`)
- Startup command syntax error

---

### Issue 7: Environment Variables Not Available

**Frontend:** Use `VITE_` prefix for client-side variables:
```typescript
// ✅ Works
const url = import.meta.env.VITE_API_URL

// ❌ Won't work (not exposed to client)
const secret = import.meta.env.API_SECRET
```

**Backend:** Set in Azure:
```bash
az webapp config appsettings set \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings DATABASE_URL="sqlite:///./app.db" SECRET_KEY="your-secret"
```

---

## Deployment Checklist

### Before First Deployment

- [ ] `requirements.txt` generated from `pyproject.toml`
- [ ] CORS configured for SWA domain
- [ ] Environment variables documented
- [ ] SQLite seeding has exception handling
- [ ] Single worker configured for SQLite

### Azure Setup

- [ ] Resource group created
- [ ] Static Web App created
- [ ] App Service Plan created (check region quota!)
- [ ] Web App created with Python runtime
- [ ] **Startup command set with `--workers 1`**
- [ ] CORS configured on backend

### GitHub Setup

- [ ] `AZURE_STATIC_WEB_APPS_API_TOKEN` secret set
- [ ] `AZURE_WEBAPP_PUBLISH_PROFILE` secret set
- [ ] `VITE_API_URL` variable set
- [ ] Workflow files include `workflow_dispatch` in conditions

### Post-Deployment Verification

- [ ] Frontend loads correctly
- [ ] Backend API responds at `/` or `/health`
- [ ] Frontend can fetch from backend (CORS working)
- [ ] Database operations work
- [ ] Check logs for any errors

---

## Quick Reference Commands

```bash
# Deploy backend manually
cd backend && az webapp up --name $WEBAPP_NAME --runtime "PYTHON:3.12"

# Stream backend logs
az webapp log tail --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP

# Restart backend
az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP

# Trigger frontend workflow
gh workflow run deploy-frontend.yml

# Check workflow status
gh run list --workflow=deploy-frontend.yml --limit 1

# Update API URL variable
gh variable set VITE_API_URL --body "https://new-backend.azurewebsites.net"

# Regenerate requirements.txt
cd backend && uv pip compile pyproject.toml -o requirements.txt
```

---

## Summary of Key Learnings

| Issue | Root Cause | Solution |
|-------|------------|----------|
| SQLite crash on startup | Multiple workers seeding DB | Use `--workers 1` |
| Module not found | Missing requirements.txt | Generate with `uv pip compile` |
| Quota exceeded | Region limits | Try `centralus` or `eastus2` |
| Workflow skipped | Missing event in condition | Add `workflow_dispatch` to `if` |
| CORS blocked | Missing origins | Configure both FastAPI & Azure |
| Container restart loop | Various | Check logs, fix startup command |

---

*Last updated: January 2026*
*Based on deployment of: https://github.com/yashness/azure-swa-demo*
