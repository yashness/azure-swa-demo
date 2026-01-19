# Azure SWA Demo

A full-stack demo application showcasing deployment to Azure Static Web Apps (frontend) and Azure App Service (backend).

## 🚀 Tech Stack

### Frontend
- **Runtime**: [Bun](https://bun.sh/) - Fast JavaScript runtime
- **Build Tool**: [Vite](https://vite.dev/) - Next generation frontend tooling
- **Language**: TypeScript

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- **Database**: SQLite with [SQLAlchemy](https://www.sqlalchemy.org/) ORM
- **Package Manager**: [uv](https://docs.astral.sh/uv/) by Astral
- **Python Version**: 3.14

### DevOps
- **Container**: DevContainer for consistent development environment
- **CI/CD**: GitHub Actions
- **Frontend Hosting**: Azure Static Web Apps
- **Backend Hosting**: Azure App Service (Linux)

## 📁 Project Structure

```
azure-workshop/
├── frontend/               # Vite + Bun frontend
│   ├── src/
│   │   ├── main.ts        # Main entry point
│   │   └── style.css      # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── backend/                # FastAPI backend
│   ├── main.py            # API endpoints
│   ├── pyproject.toml
│   └── uv.lock
├── .devcontainer/         # DevContainer config
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   └── Dockerfile
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml
│       └── deploy-backend.yml
├── README.md
└── AGENTS.md
```

## 🛠️ Local Development

### Prerequisites
- [Bun](https://bun.sh/) (for frontend)
- [uv](https://docs.astral.sh/uv/) (for backend)
- Python 3.14+
- Docker (optional, for DevContainer)

### Using DevContainer (Recommended)
1. Open the project in VS Code
2. Install the "Dev Containers" extension
3. Click "Reopen in Container" when prompted
4. Everything will be set up automatically

### Manual Setup

#### Frontend
```bash
cd frontend
bun install
bun run dev
```
Frontend will be available at http://localhost:5173

#### Backend
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```
API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check / Welcome message |
| GET | `/health` | Health status |
| GET | `/users` | List all users |
| GET | `/users/{id}` | Get user by ID |

## 🚀 Deployment

### Prerequisites
1. Azure subscription
2. GitHub repository
3. Azure CLI installed locally

### Setup Azure Resources

#### 1. Create Resource Group
```bash
az group create --name azure-swa-demo-rg --location eastus
```

#### 2. Create Azure Static Web App (Frontend)
```bash
az staticwebapp create \
  --name azure-swa-demo-frontend \
  --resource-group azure-swa-demo-rg \
  --location eastus2
```

Get the deployment token:
```bash
az staticwebapp secrets list \
  --name azure-swa-demo-frontend \
  --resource-group azure-swa-demo-rg
```

Add `AZURE_STATIC_WEB_APPS_API_TOKEN` to your GitHub repository secrets.

#### 3. Create Azure App Service (Backend)
```bash
# Create App Service Plan
az appservice plan create \
  --name azure-swa-demo-plan \
  --resource-group azure-swa-demo-rg \
  --is-linux \
  --sku B1

# Create Web App
az webapp create \
  --name azure-swa-demo-api \
  --resource-group azure-swa-demo-rg \
  --plan azure-swa-demo-plan \
  --runtime "PYTHON:3.14"

# Configure startup command
az webapp config set \
  --name azure-swa-demo-api \
  --resource-group azure-swa-demo-rg \
  --startup-file "gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
```

#### 4. Create Azure Service Principal for GitHub Actions
```bash
az ad sp create-for-rbac \
  --name "azure-swa-demo-sp" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/azure-swa-demo-rg \
  --sdk-auth
```

Add the JSON output as `AZURE_CREDENTIALS` to your GitHub repository secrets.

#### 5. Configure Environment Variables

Add `VITE_API_URL` as a repository variable pointing to your backend URL:
```
https://azure-swa-demo-api.azurewebsites.net
```

## 🔒 Security Considerations

- CORS is currently set to allow all origins (`*`). For production, configure specific origins.
- Use Azure Managed Identity for database connections in production.
- Enable HTTPS only on both frontend and backend.
- Configure proper authentication for the API.

## 📝 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
