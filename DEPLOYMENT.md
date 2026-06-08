# 🚀 NutriAI Health Portal — Deployment Guide

Complete deployment guide for the NutriAI Health Portal on Microsoft Azure. This document covers prerequisites, infrastructure provisioning with Terraform, application deployment, monitoring setup, and operational procedures.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Architecture Overview](#2-architecture-overview)
3. [Azure Account Setup](#3-azure-account-setup)
4. [Terraform State Backend](#4-terraform-state-backend)
5. [Infrastructure Provisioning](#5-infrastructure-provisioning)
6. [Database Setup](#6-database-setup)
7. [Container Registry & Image Build](#7-container-registry--image-build)
8. [Backend Deployment](#8-backend-deployment)
9. [Frontend Deployment](#9-frontend-deployment)
10. [Azure Function App (OCR)](#10-azure-function-app-ocr)
11. [Microsoft Entra ID (SSO)](#11-microsoft-entra-id-sso)
12. [Service Bus Configuration](#12-service-bus-configuration)
13. [Email Configuration](#13-email-configuration)
14. [Monitoring & Alerts](#14-monitoring--alerts)
15. [SSL/TLS & Custom Domain](#15-ssltls--custom-domain)
16. [CI/CD Pipeline](#16-cicd-pipeline)
17. [Local Development](#17-local-development)
18. [Troubleshooting](#18-troubleshooting)
19. [Operational Procedures](#19-operational-procedures)
20. [Cost Estimation](#20-cost-estimation)

---

## 1. Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Azure CLI | ≥ 2.55 | Azure resource management |
| Terraform | ≥ 1.5.0 | Infrastructure as Code |
| Docker | ≥ 24.0 | Container builds |
| Docker Compose | ≥ 2.20 | Local development |
| Node.js | ≥ 20.0 | Frontend build |
| Python | ≥ 3.11 | Backend development |
| Git | ≥ 2.40 | Version control |

### Required Azure Services

- Azure Resource Group
- Azure Virtual Network
- Azure Key Vault
- Azure Database for PostgreSQL Flexible Server
- Azure Storage Account (Blob)
- Azure Container Registry
- Azure App Service (Linux)
- Azure Static Web App
- Azure OpenAI Service
- Azure Service Bus
- Azure Function App
- Azure Application Insights
- Azure Log Analytics Workspace
- Azure Monitor Alerts
- Microsoft Entra ID (Azure AD)

### Required Azure Permissions

- **Subscription**: Contributor role
- **Azure AD**: Application Administrator (for Entra ID app registration)
- **OpenAI**: Cognitive Services Contributor

### Installation

```bash
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Terraform
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Docker
curl -fsSL https://get.docker.com | sudo sh

# Node.js (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
```

---

## 2. Architecture Overview

### Service Port Map

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Entry point, JWT validation, request routing |
| Auth Service | 8001 | Authentication, registration, Microsoft SSO |
| Document Service | 8002 | File upload, Azure Blob, OCR trigger |
| Diet Service | 8003 | GPT-4 diet generation, PDF, Service Bus |
| Health Service | 8004 | Health metrics logging, chart data |
| Notification Service | 8005 | Service Bus consumer, email sending |
| Profile Service | 8006 | User profiles, allergies, medical info |
| Admin Service | 8007 | Admin dashboard, user management |
| Frontend (Dev) | 3000 | React development server |
| Frontend (Prod) | 80 | Nginx serving React build |
| PostgreSQL | 5432 | Shared database |
| Redis | 6379 | Caching (optional) |

### Data Flow

```
User → React SPA → Nginx/SWA → API Gateway (JWT) → Microservice → PostgreSQL
                                       ↓
                                  Azure Blob Storage
                                  Azure OpenAI (GPT-4)
                                  Azure Service Bus → Notification Service → Email
                                  Azure Function App (OCR)
```

### Authentication Flow

```
1. User submits login form
2. Auth Service validates credentials, generates JWT
3. JWT set as HttpOnly cookie via Set-Cookie header
4. Subsequent requests include cookie automatically (withCredentials)
5. API Gateway extracts JWT, validates, injects X-User-ID header
6. Downstream services trust X-User-ID from API Gateway
```

### Microsoft SSO Flow

```
1. User clicks "Sign in with Microsoft"
2. Frontend redirects to /auth/microsoft
3. Auth Service generates MSAL auth URL
4. User authenticates with Microsoft
5. Microsoft redirects to /auth/microsoft/callback
6. Auth Service exchanges code for tokens
7. User created/matched in DB, JWT cookie set
8. Redirect to /dashboard
```

---

## 3. Azure Account Setup

### Login and Set Subscription

```bash
# Login to Azure
az login

# List subscriptions
az account list --output table

# Set active subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify
az account show --output table
```

### Register Required Providers

```bash
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.ServiceBus
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Network
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationalInsights
```

---

## 4. Terraform State Backend

Create the remote state storage before running Terraform:

```bash
# Create resource group for Terraform state
az group create \
  --name nutriai-terraform-state \
  --location eastus

# Create storage account (must be globally unique)
az storage account create \
  --name nutriaitfstate \
  --resource-group nutriai-terraform-state \
  --location eastus \
  --sku Standard_LRS \
  --encryption-services blob

# Get storage account key
ACCOUNT_KEY=$(az storage account keys list \
  --resource-group nutriai-terraform-state \
  --account-name nutriaitfstate \
  --query '[0].value' -o tsv)

# Create blob container
az storage container create \
  --name tfstate \
  --account-name nutriaitfstate \
  --account-key $ACCOUNT_KEY
```

---

## 5. Infrastructure Provisioning

### Configure Variables

```bash
cd terraform/

# Copy and edit the variables file
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
project_name = "nutriai"
environment  = "prod"
location     = "eastus"

admin_email = "your-admin@email.com"

# Microsoft Entra ID (leave empty to create via Terraform)
entra_client_id     = ""
entra_client_secret = ""
entra_tenant_id     = ""

# OpenAI model deployment name
openai_model_deployment = "gpt-4"

# Email
smtp_host     = "smtp.gmail.com"
smtp_port     = 587
smtp_username = "your-email@gmail.com"
smtp_password = "your-app-password"

# Azure SKUs
app_service_sku = "B2"     # B1, B2, B3, S1, S2, S3, P1v3, P2v3
postgres_sku    = "B_Standard_B1ms"  # B_Standard_B1ms, GP_Standard_D2s_v3
```

### Initialize and Apply

```bash
# Initialize Terraform (downloads providers, configures backend)
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Save outputs
terraform output -json > ../deployment-outputs.json
```

### Terraform Module Dependency Graph

```
resource_group
    ├── vnet
    │   ├── postgresql (uses postgres_subnet)
    │   └── app_service (uses app_service_subnet)
    ├── key_vault
    ├── storage
    ├── container_registry
    ├── app_service_plan
    │   ├── app_service
    │   └── function_app
    ├── openai
    ├── service_bus
    ├── monitoring
    │   └── alerts
    ├── static_web_app
    └── entra_id
```

---

## 6. Database Setup

PostgreSQL is provisioned by Terraform. After provisioning:

### Verify Connection

```bash
# Get the FQDN from Terraform output
DB_FQDN=$(terraform output -raw database_fqdn)

# Test connection (requires VPN/VNet peering since it's private)
psql "postgresql://nutriai_admin:$(terraform output -raw db_password)@${DB_FQDN}:5432/nutriai?sslmode=require"
```

### Database Schema

The schema is automatically created by SQLAlchemy's `Base.metadata.create_all()` on each service startup. Tables created:

| Table | Service | Description |
|-------|---------|-------------|
| `users` | Auth, Profile, Diet, Admin | User accounts |
| `patient_profiles` | Profile | Medical conditions, preferences |
| `food_allergies` | Profile, Diet | Allergen tracking |
| `documents` | Document, Diet, Admin | Uploaded medical documents |
| `diet_plans` | Diet, Admin | AI-generated diet plans |
| `health_logs` | Health, Admin | Daily health metrics |
| `meal_logs` | Health | Meal tracking |
| `notifications` | Notification | In-app notifications |

### Manual Migration (if needed)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify tables exist
\dt

-- Check table schemas
\d users
\d diet_plans
```

---

## 7. Container Registry & Image Build

### Login to ACR

```bash
ACR_NAME=$(terraform output -raw container_registry_login_server)

# Login
az acr login --name ${ACR_NAME%%.*}
```

### Build and Push Backend Image

```bash
# From project root
docker build -f Dockerfile.backend -t nutriai-backend:latest .

# Tag for ACR
docker tag nutriai-backend:latest ${ACR_NAME}/nutriai-backend:latest
docker tag nutriai-backend:latest ${ACR_NAME}/nutriai-backend:$(git rev-parse --short HEAD)

# Push
docker push ${ACR_NAME}/nutriai-backend:latest
docker push ${ACR_NAME}/nutriai-backend:$(git rev-parse --short HEAD)
```

### Build and Push Frontend Image

```bash
cd frontend/

docker build -t nutriai-frontend:latest .

docker tag nutriai-frontend:latest ${ACR_NAME}/nutriai-frontend:latest
docker push ${ACR_NAME}/nutriai-frontend:latest
```

---

## 8. Backend Deployment

### App Service Configuration

The backend runs all 8 microservices in a single container via supervisord. Terraform configures the App Service, but you can update settings:

```bash
APP_NAME="nutriai-prod-backend"

# Verify deployment
az webapp show --name $APP_NAME --resource-group nutriai-prod-rg --query state

# View logs
az webapp log tail --name $APP_NAME --resource-group nutriai-prod-rg

# Restart
az webapp restart --name $APP_NAME --resource-group nutriai-prod-rg

# Check health
curl https://${APP_NAME}.azurewebsites.net/health
```

### Environment Variables

All environment variables are set by Terraform. To update manually:

```bash
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group nutriai-prod-rg \
  --settings \
    AZURE_OPENAI_KEY="new-key" \
    JWT_SECRET_KEY="new-secret"
```

### Scaling

```bash
# Scale up (more powerful machine)
az appservice plan update \
  --name nutriai-prod-asp \
  --resource-group nutriai-prod-rg \
  --sku P1v3

# Scale out (more instances)
az webapp update \
  --name $APP_NAME \
  --resource-group nutriai-prod-rg \
  --set siteConfig.numberOfWorkers=3
```

---

## 9. Frontend Deployment

### Option A: Azure Static Web App (Recommended)

```bash
cd frontend/

# Build the React app
npm install
npm run build

# Deploy using SWA CLI
npm install -g @azure/static-web-apps-cli

swa deploy ./dist \
  --deployment-token $(terraform output -raw static_web_app_api_key) \
  --env production
```

### Option B: Nginx Container on App Service

The frontend Dockerfile builds the React app and serves it via Nginx with API proxying:

```bash
docker build -t nutriai-frontend:latest .
docker tag nutriai-frontend:latest ${ACR_NAME}/nutriai-frontend:latest
docker push ${ACR_NAME}/nutriai-frontend:latest
```

### Option C: Azure CDN + Storage Account

```bash
# Upload build artifacts to blob storage
az storage blob upload-batch \
  --destination '$web' \
  --source ./dist \
  --account-name nutriaiprodfrontend \
  --overwrite
```

---

## 10. Azure Function App (OCR)

The Function App processes uploaded documents using Azure Document Intelligence:

### Deploy Function Code

```bash
cd function-app/

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Deploy
func azure functionapp publish nutriai-prod-func --python
```

### Function App Structure

```python
# function_app.py
import azure.functions as func
from azure.ai.formrecognizer import DocumentAnalysisClient

app = func.FunctionApp()

@app.function_name(name="ProcessDocument")
@app.route(route="process-document", methods=["POST"])
def process_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    1. Receives document_id and blob_name
    2. Downloads blob from Azure Storage
    3. Sends to Azure Document Intelligence for OCR
    4. Updates document.ocr_content and ocr_status in database
    """
    # Implementation handles PDF/image OCR extraction
    pass
```

### Verify Function App

```bash
# Check status
az functionapp show \
  --name nutriai-prod-func \
  --resource-group nutriai-prod-rg \
  --query state

# Test invocation
curl -X POST \
  "https://nutriai-prod-func.azurewebsites.net/api/process-document" \
  -H "x-functions-key: YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test-id", "blob_name": "test.pdf"}'
```

---

## 11. Microsoft Entra ID (SSO)

### Terraform-Created App Registration

Terraform creates the Entra ID app registration automatically. To configure manually:

```bash
# Create app registration
az ad app create \
  --display-name "NutriAI Health Portal" \
  --web-redirect-uris "https://nutriai-prod-backend.azurewebsites.net/auth/microsoft/callback" \
  --required-resource-accesses '[{
    "resourceAppId": "00000003-0000-0000-c000-000000000000",
    "resourceAccess": [
      {"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"},
      {"id": "64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0", "type": "Scope"},
      {"id": "14dad69e-099b-42c9-810b-d002981feec1", "type": "Scope"}
    ]
  }]'
```

### Required API Permissions

| Permission | Type | Description |
|-----------|------|-------------|
| User.Read | Delegated | Sign in and read user profile |
| email | Delegated | View user's email address |
| profile | Delegated | View user's basic profile |

### Auth Service Configuration

Set these environment variables on the backend:

```
ENTRA_CLIENT_ID=<from az ad app list>
ENTRA_CLIENT_SECRET=<from az ad app credential reset>
ENTRA_TENANT_ID=<from az account show>
ENTRA_REDIRECT_URI=https://your-backend.azurewebsites.net/auth/microsoft/callback
```

---

## 12. Service Bus Configuration

### Topic and Subscription

Terraform creates these automatically:

- **Topic**: `meal-reminders`
- **Subscription**: `email-sender` (max delivery count: 5)

### Message Format

Each meal reminder message contains:

```json
{
  "user_id": "uuid",
  "user_email": "patient@example.com",
  "meal_type": "breakfast",
  "foods_to_eat": [
    {"food_name": "Oatmeal", "portion_size": "1 cup", "timing": "Morning"}
  ],
  "foods_to_avoid": [
    {"food_name": "Peanuts", "reason": "Severe allergy", "risk_level": "high"}
  ],
  "day_name": "Monday",
  "meal_description": "Steel-cut oatmeal with berries and honey"
}
```

### Verify Service Bus

```bash
# Check namespace
az servicebus namespace show \
  --name nutriai-prod-sb \
  --resource-group nutriai-prod-rg

# Check topic
az servicebus topic show \
  --name meal-reminders \
  --namespace-name nutriai-prod-sb \
  --resource-group nutriai-prod-rg

# Check subscription message count
az servicebus topic subscription show \
  --name email-sender \
  --topic-name meal-reminders \
  --namespace-name nutriai-prod-sb \
  --resource-group nutriai-prod-rg \
  --query countDetails
```

---

## 13. Email Configuration

### Option A: Gmail SMTP

```bash
# 1. Enable 2-Factor Authentication on Gmail
# 2. Generate App Password: Google Account → Security → App passwords
# 3. Set environment variables:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App password
```

### Option B: SendGrid

```bash
# 1. Create SendGrid account
# 2. Generate API key
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@nutriai-health.com
```

### Email Template

The notification service sends styled HTML emails with:
- NutriAI branded header (green-blue gradient)
- Foods to eat table (green theme)
- Foods to avoid table (red theme)
- Call-to-action button linking to the portal

---

## 14. Monitoring & Alerts

### Application Insights

Terraform provisions Application Insights automatically. Connection string is injected into all services.

```bash
# View Application Insights
az monitor app-insights component show \
  --app nutriai-prod-monitor-appinsights \
  --resource-group nutriai-prod-rg

# Query logs (last 1 hour)
az monitor app-insights query \
  --app nutriai-prod-monitor-appinsights \
  --resource-group nutriai-prod-rg \
  --analytics-query "requests | where timestamp > ago(1h) | summarize count() by resultCode"
```

### Configured Alerts

| Alert | Metric | Threshold | Severity |
|-------|--------|-----------|----------|
| High Response Time | HttpResponseTime (avg) | > 5 seconds | Warning |
| High Error Rate | Http5xx (total) | > 10 in 15 min | Critical |
| High CPU | CpuPercentage (avg) | > 80% | Warning |

### Health Check Endpoints

Every service exposes `/health`:

```bash
# Check all services
curl https://nutriai-prod-backend.azurewebsites.net/health

# Response
{
  "service": "api-gateway",
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-06-08T18:00:00"
}
```

### Log Access

```bash
# Stream logs
az webapp log tail \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg

# Download logs
az webapp log download \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --log-file logs.zip
```

---

## 15. SSL/TLS & Custom Domain

### Add Custom Domain

```bash
# Add custom domain
az webapp config hostname add \
  --webapp-name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --hostname api.nutriai-health.com

# Create managed SSL certificate
az webapp config ssl create \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --hostname api.nutriai-health.com

# Bind SSL
az webapp config ssl bind \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --certificate-thumbprint <THUMBPRINT> \
  --ssl-type SNI
```

### DNS Configuration

Add these DNS records:

| Type | Name | Value |
|------|------|-------|
| CNAME | api | nutriai-prod-backend.azurewebsites.net |
| CNAME | app | nutriai-prod-frontend.azurestaticapps.net |
| TXT | asuid.api | verification-id-from-azure |

---

## 16. CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy NutriAI

on:
  push:
    branches: [main]

env:
  ACR_NAME: nutriaiprodacr
  BACKEND_APP: nutriai-prod-backend

jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to ACR
        uses: azure/docker-login@v1
        with:
          login-server: ${{ env.ACR_NAME }}.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      
      - name: Build and Push
        run: |
          docker build -f Dockerfile.backend -t ${{ env.ACR_NAME }}.azurecr.io/nutriai-backend:${{ github.sha }} .
          docker push ${{ env.ACR_NAME }}.azurecr.io/nutriai-backend:${{ github.sha }}
      
      - name: Deploy to App Service
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.BACKEND_APP }}
          images: ${{ env.ACR_NAME }}.azurecr.io/nutriai-backend:${{ github.sha }}

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
      
      - name: Build Frontend
        run: |
          cd frontend
          npm ci
          npm run build
      
      - name: Deploy to Static Web App
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.SWA_TOKEN }}
          app_location: frontend
          output_location: dist

  terraform:
    runs-on: ubuntu-latest
    needs: [build-backend, build-frontend]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
      
      - name: Terraform Apply
        run: |
          cd terraform
          terraform init
          terraform apply -auto-approve
        env:
          ARM_CLIENT_ID: ${{ secrets.ARM_CLIENT_ID }}
          ARM_CLIENT_SECRET: ${{ secrets.ARM_CLIENT_SECRET }}
          ARM_SUBSCRIPTION_ID: ${{ secrets.ARM_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.ARM_TENANT_ID }}
```

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `SWA_TOKEN` | Static Web App deployment token |
| `ARM_CLIENT_ID` | Azure service principal client ID |
| `ARM_CLIENT_SECRET` | Azure service principal client secret |
| `ARM_SUBSCRIPTION_ID` | Azure subscription ID |
| `ARM_TENANT_ID` | Azure tenant ID |

---

## 17. Local Development

### Docker Compose (Full Stack)

```bash
# Start everything
docker compose up --build

# Start specific services
docker compose up postgres redis auth-service api-gateway frontend

# View logs
docker compose logs -f diet-service

# Stop everything
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Individual Service Development

```bash
# Backend service (e.g., diet-service)
cd services/diet-service
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://nutriai_user:nutriai_password@localhost:5432/nutriai
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
EOF

# Run
python main.py
```

```bash
# Frontend
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000 with API proxy to localhost:8000
```

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://nutriai_user:nutriai_password@localhost:5432/nutriai

# JWT
JWT_SECRET_KEY=super-secret-jwt-key-for-development
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-01

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER_NAME=nutriai-documents

# Azure Service Bus
AZURE_SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://...
AZURE_SERVICE_BUS_TOPIC_NAME=meal-reminders

# Function App (OCR)
FUNCTION_APP_URL=https://your-func.azurewebsites.net
FUNCTION_APP_KEY=your-function-key

# Microsoft Entra ID
ENTRA_CLIENT_ID=your-client-id
ENTRA_CLIENT_SECRET=your-client-secret
ENTRA_TENANT_ID=your-tenant-id
ENTRA_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## 18. Troubleshooting

### Common Issues

#### 1. Database Connection Refused

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check connection string
echo $DATABASE_URL

# Test connection
psql "$DATABASE_URL" -c "SELECT 1"

# In Azure: verify VNet integration and private DNS
az network private-dns record-set list \
  --zone-name nutriai-prod-vnet.private.postgres.database.azure.com \
  --resource-group nutriai-prod-rg
```

#### 2. JWT Authentication Failures

```bash
# Check JWT_SECRET_KEY is same across all services
# In Docker Compose, all services share the same env var
# In Azure, verify App Service settings:
az webapp config appsettings list \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --query "[?name=='JWT_SECRET_KEY'].value"
```

#### 3. OpenAI API Errors

```bash
# Verify deployment exists
az cognitiveservices account deployment list \
  --name nutriai-prod-openai \
  --resource-group nutriai-prod-rg

# Check quota
az cognitiveservices usage list \
  --name nutriai-prod-openai \
  --resource-group nutriai-prod-rg

# Common error: "model_not_found" → deployment name mismatch
# Common error: "rate_limit_exceeded" → increase capacity in Terraform
```

#### 4. Service Bus Messages Not Processing

```bash
# Check subscription has active messages
az servicebus topic subscription show \
  --name email-sender \
  --topic-name meal-reminders \
  --namespace-name nutriai-prod-sb \
  --resource-group nutriai-prod-rg \
  --query "countDetails"

# Check dead-letter queue
az servicebus topic subscription show \
  --name email-sender \
  --topic-name meal-reminders \
  --namespace-name nutriai-prod-sb \
  --resource-group nutriai-prod-rg \
  --query "countDetails.deadLetterMessageCount"
```

#### 5. Frontend API 404 Errors

```bash
# Verify Vite proxy is configured (development):
# vite.config.js → server.proxy → /api → http://localhost:8000

# Verify Nginx proxy is configured (production):
# nginx.conf → location /api/ → proxy_pass http://api-gateway:8000/
```

#### 6. OCR Not Processing

```bash
# Check Function App logs
az functionapp log tail \
  --name nutriai-prod-func \
  --resource-group nutriai-prod-rg

# Verify Function App has correct storage connection string
# Verify Document Intelligence endpoint is accessible
```

### Health Check Commands

```bash
# Check all service health
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  echo "Port $port: $(curl -s http://localhost:$port/health | jq -r '.status')"
done

# Docker Compose service status
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

---

## 19. Operational Procedures

### Backup Database

```bash
# Azure automated backups (configured: 7 days retention)

# Manual backup
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql "$DATABASE_URL" < backup_20260608_120000.sql
```

### Update Application

```bash
# 1. Build new image
docker build -f Dockerfile.backend -t nutriai-backend:v2 .

# 2. Push to ACR
docker tag nutriai-backend:v2 ${ACR_NAME}/nutriai-backend:v2
docker push ${ACR_NAME}/nutriai-backend:v2

# 3. Update App Service
az webapp config container set \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --docker-custom-image-name ${ACR_NAME}/nutriai-backend:v2

# 4. Restart
az webapp restart \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg
```

### Rollback

```bash
# Rollback to previous image
az webapp config container set \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --docker-custom-image-name ${ACR_NAME}/nutriai-backend:v1

az webapp restart \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg
```

### Rotate Secrets

```bash
# 1. Generate new JWT secret
NEW_SECRET=$(openssl rand -base64 48)

# 2. Update Key Vault
az keyvault secret set \
  --vault-name nutriaiprodkv \
  --name jwt-secret-key \
  --value "$NEW_SECRET"

# 3. Update App Service
az webapp config appsettings set \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg \
  --settings JWT_SECRET_KEY="$NEW_SECRET"

# 4. Restart (invalidates existing tokens)
az webapp restart \
  --name nutriai-prod-backend \
  --resource-group nutriai-prod-rg
```

### Destroy Infrastructure

```bash
cd terraform/

# Preview destruction
terraform plan -destroy

# Destroy (CAUTION: irreversible)
terraform destroy

# Remove state backend
az group delete --name nutriai-terraform-state --yes
```

---

## 20. Cost Estimation

### Monthly Cost Breakdown (Production)

| Service | SKU | Est. Monthly Cost |
|---------|-----|-------------------|
| App Service (Backend) | B2 | ~$55 |
| PostgreSQL Flexible Server | B_Standard_B1ms | ~$25 |
| Azure OpenAI (GPT-4) | S0 + usage | ~$30-100 |
| Storage Account | Standard LRS | ~$5 |
| Container Registry | Basic | ~$5 |
| Service Bus | Standard | ~$10 |
| Function App | Consumption | ~$0-5 |
| Application Insights | Pay-as-you-go | ~$5-15 |
| Static Web App | Standard | ~$9 |
| Key Vault | Standard | ~$1 |
| **Total** | | **~$145-230/mo** |

### Cost Optimization Tips

1. **Dev/Staging**: Use B1 App Service and B_Standard_B1ms PostgreSQL
2. **OpenAI**: Use `gpt-4o-mini` for lower-cost diet plan generation
3. **Function App**: Consumption plan (pay per execution)
4. **Monitoring**: Reduce Log Analytics retention to 7 days in non-prod
5. **Reserved Instances**: 1-year reservation for 30-40% savings on App Service and PostgreSQL

---

<div align="center">
  <b>🏥 NutriAI Health Portal — Deployment Guide</b><br>
  <sub>Last updated: June 2026</sub>
</div>
