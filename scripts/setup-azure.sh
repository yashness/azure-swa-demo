#!/bin/bash
# Azure Setup Script for azure-swa-demo
# Run this script to create all necessary Azure resources

set -e

# Configuration - Update these values
RESOURCE_GROUP="azure-swa-demo-rg"
LOCATION="eastus"
SWA_NAME="azure-swa-demo-frontend"
APP_SERVICE_PLAN="azure-swa-demo-plan"
WEBAPP_NAME="azure-swa-demo-api"

echo "🚀 Setting up Azure resources for azure-swa-demo..."

# Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Static Web App
echo "🌐 Creating Static Web App..."
az staticwebapp create \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --location "eastus2"

# Get SWA deployment token
echo "🔑 Getting SWA deployment token..."
SWA_TOKEN=$(az staticwebapp secrets list --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "properties.apiKey" -o tsv)
echo "Add this token as AZURE_STATIC_WEB_APPS_API_TOKEN in GitHub secrets:"
echo "$SWA_TOKEN"

# Create App Service Plan
echo "📋 Creating App Service Plan..."
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B1

# Create Web App
echo "🖥️ Creating Web App..."
az webapp create \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime "PYTHON:3.12"

# Configure startup command
echo "⚙️ Configuring Web App..."
az webapp config set \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"

# Enable CORS
az webapp cors add \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "*"

# Create Service Principal for GitHub Actions
echo "🔐 Creating Service Principal for GitHub Actions..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "azure-swa-demo-sp" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth)

echo ""
echo "Add this JSON as AZURE_CREDENTIALS in GitHub secrets:"
echo "$SP_OUTPUT"

# Get URLs
SWA_URL=$(az staticwebapp show --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "defaultHostname" -o tsv)
WEBAPP_URL=$(az webapp show --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP --query "defaultHostName" -o tsv)

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Summary:"
echo "  Frontend URL: https://$SWA_URL"
echo "  Backend URL: https://$WEBAPP_URL"
echo ""
echo "🔧 Next steps:"
echo "  1. Add AZURE_STATIC_WEB_APPS_API_TOKEN to GitHub secrets"
echo "  2. Add AZURE_CREDENTIALS to GitHub secrets"
echo "  3. Add VITE_API_URL=https://$WEBAPP_URL as GitHub repository variable"
echo "  4. Push to main branch to trigger deployment"
