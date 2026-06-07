# 🚀 NutriAI Health Portal - Azure Portal Deployment Guide

> Step-by-step guide to deploying the NutriAI Health Portal using the **Azure Portal** (GUI). Every step includes exact navigation paths and field values.

---

## 📋 Prerequisites

- An **Azure account** with an active subscription ([Create one free](https://azure.microsoft.com/free/))
- **Owner** or **Contributor** role on the subscription
- [Docker Desktop](https://www.docker.com/get-started/) installed locally (for building the container image)
- The project source code on your local machine

---

## Step 1: Create a Resource Group

A Resource Group is a container that holds all related Azure resources.

1. Go to the [Azure Portal](https://portal.azure.com)
2. In the top search bar, type **"Resource groups"** and select it
3. Click **"+ Create"**
4. Fill in:
   | Field | Value |
   |-------|-------|
   | Subscription | *Select your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Region | `East US` *(or your preferred region)* |
5. Click **"Review + create"** → **"Create"**

> [!TIP]
> Choose a region close to your users. All subsequent resources should be created in the **same region** for best performance and to avoid cross-region data transfer costs.

---

## Step 2: Create Azure Key Vault

Key Vault securely stores all secrets (API keys, connection strings, passwords).

1. Search **"Key vaults"** in the portal search bar → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Key vault name | `kv-nutriai-prod` *(must be globally unique)* |
   | Region | `East US` |
   | Pricing tier | **Standard** |
3. **Access configuration** tab:
   - Permission model: **Azure role-based access control (RBAC)**
4. Click **"Review + create"** → **"Create"**
5. After deployment, go to the Key Vault resource
6. Go to **"Access control (IAM)"** in the left menu
7. Click **"+ Add"** → **"Add role assignment"**
   - Role: **Key Vault Secrets Officer**
   - Members: Select your own Azure account
   - Click **"Review + assign"**

> [!IMPORTANT]
> You'll come back to Key Vault later to store secrets after creating each service.

---

## Step 3: Create Azure Storage Account

Azure Blob Storage holds uploaded medical documents.

1. Search **"Storage accounts"** → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Storage account name | `stnutriaiprod` *(must be globally unique, lowercase, no dashes)* |
   | Region | `East US` |
   | Performance | **Standard** |
   | Redundancy | **Locally-redundant storage (LRS)** |
3. **Advanced** tab:
   - Minimum TLS version: **Version 1.2**
   - Allow Blob anonymous access: **Disabled** ☐
4. Click **"Review + create"** → **"Create"**

### Create the Blob Container

5. Go to the storage account resource after deployment
6. In the left menu, under **"Data storage"**, click **"Containers"**
7. Click **"+ Container"**
   | Field | Value |
   |-------|-------|
   | Name | `health-documents` |
   | Anonymous access level | **Private (no anonymous access)** |
8. Click **"Create"**

### Copy the Connection String

9. In the left menu, go to **"Security + networking"** → **"Access keys"**
10. Click **"Show"** next to Key 1's Connection string
11. Click the **copy icon** — save this for later

### Store in Key Vault

12. Go back to your Key Vault (`kv-nutriai-prod`)
13. Left menu → **"Objects"** → **"Secrets"** → **"+ Generate/Import"**
    | Field | Value |
    |-------|-------|
    | Name | `storage-connection-string` |
    | Secret value | *Paste the connection string you copied* |
14. Click **"Create"**

---

## Step 4: Create PostgreSQL Flexible Server

PostgreSQL is the application's primary database.

1. Search **"Azure Database for PostgreSQL flexible servers"** → Click **"+ Create"**
2. Select **"Flexible server"** → **"Create"**
3. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Server name | `psql-nutriai-prod` *(must be globally unique)* |
   | Region | `East US` |
   | PostgreSQL version | **15** |
   | Workload type | **Development** *(cheapest; use Production for live workloads)* |
   | Compute + storage | Click **"Configure server"** → Select **Burstable, B2s** → **"Save"** |
   | Authentication method | **PostgreSQL authentication only** |
   | Admin username | `nutriai_admin` |
   | Password | *Create a strong password and save it* |
4. **Networking** tab:
   - Connectivity method: **Public access (allowed IP addresses)**
   - Check ✅ **"Allow public access from any Azure service within Azure to this server"**
   - Click **"+ Add current client IP address"** (for local development)
5. Click **"Review + create"** → **"Create"** *(takes 5-10 minutes)*

### Create the Application Database

6. After deployment, go to the PostgreSQL server resource
7. Left menu → **"Settings"** → **"Databases"**
8. Click **"+ Add"**
   | Field | Value |
   |-------|-------|
   | Name | `nutriai` |
9. Click **"Save"**

### Build the Connection String

Your database URL is:
```
postgresql://nutriai_admin:<YOUR_PASSWORD>@psql-nutriai-prod.postgres.database.azure.com:5432/nutriai?sslmode=require
```

### Store in Key Vault

10. Go to Key Vault → **"Secrets"** → **"+ Generate/Import"**
    | Field | Value |
    |-------|-------|
    | Name | `database-url` |
    | Secret value | *Paste the connection string above (with your actual password)* |
11. Click **"Create"**

---

## Step 5: Create Azure OpenAI Service

Azure OpenAI powers the AI diet plan generation.

1. Search **"Azure OpenAI"** → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Region | `East US` |
   | Name | `oai-nutriai-prod` |
   | Pricing tier | **Standard S0** |
3. Click **"Review + submit"** → **"Create"**

### Deploy the GPT-4 Model

4. After deployment, go to the resource → Click **"Go to Azure OpenAI Studio"**  
   *(or navigate to [Azure AI Foundry](https://ai.azure.com))*
5. In the left menu, click **"Deployments"** → **"+ Create deployment"**
   | Field | Value |
   |-------|-------|
   | Model | **gpt-4** |
   | Deployment name | `gpt-4` |
   | Deployment type | **Standard** |
   | Tokens per Minute Rate Limit | `30K` *(adjust based on your needs)* |
6. Click **"Create"**

### Copy Endpoint and Key

7. Go back to the Azure OpenAI resource in the portal (not AI Studio)
8. Left menu → **"Resource Management"** → **"Keys and Endpoint"**
9. Copy:
   - **Endpoint** (e.g., `https://oai-nutriai-prod.openai.azure.com/`)
   - **Key 1** — save both for later

### Store in Key Vault

10. Go to Key Vault → **"Secrets"** → **"+ Generate/Import"**
    | Field | Value |
    |-------|-------|
    | Name | `openai-key` |
    | Secret value | *Paste Key 1* |
11. Click **"Create"**

---

## Step 6: Create Azure Document Intelligence

Document Intelligence handles OCR (text extraction) from medical documents.

1. Search **"Document Intelligence"** (or "Azure AI Document Intelligence") → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Region | `East US` |
   | Name | `di-nutriai-prod` |
   | Pricing tier | **Standard S0** |
3. Click **"Review + create"** → **"Create"**

### Copy Endpoint and Key

4. After deployment, go to the resource
5. Left menu → **"Resource Management"** → **"Keys and Endpoint"**
6. Copy:
   - **Endpoint** (e.g., `https://di-nutriai-prod.cognitiveservices.azure.com/`)
   - **Key 1**

### Store in Key Vault

7. Go to Key Vault → **"Secrets"** → **"+ Generate/Import"**
   | Field | Value |
   |-------|-------|
   | Name | `doc-intelligence-key` |
   | Secret value | *Paste Key 1* |
8. Click **"Create"**

---

## Step 7: Create Azure Container Registry (ACR)

ACR stores your Docker image so App Service can pull it.

1. Search **"Container registries"** → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Registry name | `acrnutriaiprod` *(must be globally unique, alphanumeric only)* |
   | Region | `East US` |
   | SKU | **Basic** |
3. Click **"Review + create"** → **"Create"**

### Enable Admin User

4. After deployment, go to the ACR resource
5. Left menu → **"Settings"** → **"Access keys"**
6. Toggle **"Admin user"** to **Enabled**
7. Copy the **Login server**, **Username**, and **password** — you'll need these

### Build and Push Your Docker Image

Open a terminal on your local machine in the project directory:

```bash
# Login to ACR
docker login acrnutriaiprod.azurecr.io -u <username> -p <password>

# Build the image
docker build -t nutriai-health-portal:latest .

# Tag for ACR
docker tag nutriai-health-portal:latest acrnutriaiprod.azurecr.io/nutriai-health-portal:latest

# Push to ACR
docker push acrnutriaiprod.azurecr.io/nutriai-health-portal:latest
```

> [!TIP]
> You can verify the image was pushed by going to **ACR → "Services" → "Repositories"** in the portal. You should see `nutriai-health-portal` listed.

---

## Step 8: Create Azure App Service

App Service hosts the web application.

### Create the App Service Plan

1. Search **"App Service plans"** → Click **"+ Create"**
2. Fill in:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Name | `plan-nutriai-prod` |
   | Operating System | **Linux** |
   | Region | `East US` |
   | Pricing plan | **Basic B2** *(or Standard S1 for production)* |
3. Click **"Review + create"** → **"Create"**

### Create the Web App

4. Search **"App Services"** → Click **"+ Create"** → **"Web App"**
5. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Name | `app-nutriai-prod` *(becomes app-nutriai-prod.azurewebsites.net)* |
   | Publish | **Container** |
   | Operating System | **Linux** |
   | Region | `East US` |
   | App Service Plan | `plan-nutriai-prod` |
6. **Container** tab:
   | Field | Value |
   |-------|-------|
   | Image Source | **Azure Container Registry** |
   | Registry | `acrnutriaiprod` |
   | Image | `nutriai-health-portal` |
   | Tag | `latest` |
7. Click **"Review + create"** → **"Create"**

### Configure Environment Variables

8. After deployment, go to the App Service resource
9. Left menu → **"Settings"** → **"Environment variables"**
10. Click **"+ Add"** for each of the following:

| Name | Value |
|------|-------|
| `SECRET_KEY` | *A random 64-character string (generate at random.org)* |
| `DATABASE_URL` | `postgresql://nutriai_admin:<PASSWORD>@psql-nutriai-prod.postgres.database.azure.com:5432/nutriai?sslmode=require` |
| `AZURE_STORAGE_CONNECTION_STRING` | *Connection string from Step 3* |
| `AZURE_STORAGE_CONTAINER_NAME` | `health-documents` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | *Endpoint from Step 6* |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | *Key from Step 6* |
| `AZURE_OPENAI_ENDPOINT` | *Endpoint from Step 5* |
| `AZURE_OPENAI_KEY` | *Key from Step 5* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4` |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` |
| `AZURE_KEYVAULT_URL` | `https://kv-nutriai-prod.vault.azure.net` |
| `WEBSITES_PORT` | `8000` |

11. Click **"Apply"** at the bottom → **"Confirm"**

### Enable HTTPS Only

12. Left menu → **"Settings"** → **"Configuration"**
13. Under **"General settings"** tab:
    - **HTTPS Only**: Toggle to **On**
    - **Minimum TLS Version**: **1.2**
14. Click **"Save"**

### Enable Managed Identity (for Key Vault)

15. Left menu → **"Settings"** → **"Identity"**
16. Under **"System assigned"** tab:
    - Status: Toggle to **On**
17. Click **"Save"** → **"Yes"** to confirm
18. Copy the **Object (principal) ID** that appears

### Grant Key Vault Access to App Service

19. Go back to your Key Vault (`kv-nutriai-prod`)
20. Left menu → **"Access control (IAM)"**
21. Click **"+ Add"** → **"Add role assignment"**
    - Role: **Key Vault Secrets User**
    - Members tab → **"+ Select members"** → Search for `app-nutriai-prod` → Select it
22. Click **"Review + assign"**

> [!IMPORTANT]
> After configuring all settings, the App Service will automatically restart and pull the container image. Wait 2-3 minutes, then visit `https://app-nutriai-prod.azurewebsites.net` to verify.

---

## Step 9: Create Azure Function App

The Function App processes documents in the background and performs cleanup.

### Create a Storage Account for Functions

1. Search **"Storage accounts"** → Click **"+ Create"**
2. Fill in:
   | Field | Value |
   |-------|-------|
   | Resource group | `rg-nutriai-prod` |
   | Storage account name | `stnutraifuncprod` |
   | Region | `East US` |
   | Performance | **Standard** |
   | Redundancy | **LRS** |
3. Click **"Review + create"** → **"Create"**

### Create the Function App

4. Search **"Function App"** → Click **"+ Create"** → Select **"Consumption"**
5. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Function App name | `func-nutriai-prod` |
   | Runtime stack | **Python** |
   | Version | **3.11** |
   | Region | `East US` |
   | Operating System | **Linux** |
6. **Storage** tab:
   - Storage account: `stnutraifuncprod`
7. Click **"Review + create"** → **"Create"**

### Configure Function App Settings

8. After deployment, go to the Function App resource
9. Left menu → **"Settings"** → **"Environment variables"**
10. Click **"+ Add"** for each:

| Name | Value |
|------|-------|
| `DATABASE_URL` | *Same database URL from Step 4* |
| `AZURE_STORAGE_CONNECTION_STRING` | *Connection string from Step 3* |
| `AZURE_STORAGE_CONTAINER_NAME` | `health-documents` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | *Endpoint from Step 6* |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | *Key from Step 6* |

11. Click **"Apply"** → **"Confirm"**

### Deploy Function App Code

On your local machine, install Azure Functions Core Tools and deploy:

```bash
# Install Azure Functions Core Tools (if not already installed)
npm install -g azure-functions-core-tools@4

# Navigate to function app directory
cd function_app

# Deploy to Azure
func azure functionapp publish func-nutriai-prod --python
```

### Get Function App URL and Key

12. In the portal, go to Function App → Left menu → **"Functions"**
13. Click on **"process_documents"** function
14. Click **"Get Function URL"** → Copy the URL (includes the function key)
15. Go back to the App Service (`app-nutriai-prod`)
16. **"Environment variables"** → Add:

| Name | Value |
|------|-------|
| `FUNCTION_APP_URL` | `https://func-nutriai-prod.azurewebsites.net` |
| `FUNCTION_APP_KEY` | *The function key from the URL query parameter `?code=...`* |

17. Click **"Apply"** → **"Confirm"**

---

## Step 10: Register Microsoft Entra ID Application (SSO)

This enables "Sign in with Microsoft" for your users.

1. Search **"Microsoft Entra ID"** (formerly Azure Active Directory) → Select it
2. Left menu → **"App registrations"** → **"+ New registration"**
3. Fill in:
   | Field | Value |
   |-------|-------|
   | Name | `NutriAI Health Portal` |
   | Supported account types | **Accounts in this organizational directory only** |
   | Redirect URI (Web) | `https://app-nutriai-prod.azurewebsites.net/auth/callback` |
4. Click **"Register"**

### Copy Application IDs

5. On the app's **Overview** page, copy:
   - **Application (client) ID** → Save as `ENTRA_CLIENT_ID`
   - **Directory (tenant) ID** → Save as `ENTRA_TENANT_ID`

### Create a Client Secret

6. Left menu → **"Certificates & secrets"** → **"Client secrets"** tab
7. Click **"+ New client secret"**
   | Field | Value |
   |-------|-------|
   | Description | `NutriAI Portal Secret` |
   | Expires | **24 months** *(or your preference)* |
8. Click **"Add"**
9. **Immediately copy the "Value"** (not the Secret ID) — this is shown only once!
   → Save as `ENTRA_CLIENT_SECRET`

### Configure API Permissions

10. Left menu → **"API permissions"**
11. Verify that **Microsoft Graph → User.Read** is already listed (it should be by default)
12. If not, click **"+ Add a permission"** → **"Microsoft Graph"** → **"Delegated permissions"** → Check **"User.Read"** → **"Add permissions"**

### Update App Service Environment Variables

13. Go back to App Service → **"Environment variables"** → Add:

| Name | Value |
|------|-------|
| `ENTRA_CLIENT_ID` | *Application (client) ID from step 5* |
| `ENTRA_CLIENT_SECRET` | *Client secret value from step 9* |
| `ENTRA_TENANT_ID` | *Directory (tenant) ID from step 5* |
| `ENTRA_REDIRECT_URI` | `https://app-nutriai-prod.azurewebsites.net/auth/callback` |

14. Click **"Apply"** → **"Confirm"**

---

## Step 11: Set Up Application Insights (Monitoring)

Application Insights provides logging, performance monitoring, and error tracking.

1. Search **"Application Insights"** → Click **"+ Create"**
2. **Basics** tab:
   | Field | Value |
   |-------|-------|
   | Subscription | *Your subscription* |
   | Resource group | `rg-nutriai-prod` |
   | Name | `ai-nutriai-prod` |
   | Region | `East US` |
   | Resource Mode | **Workspace-based** |
   | Log Analytics Workspace | **Create new** → Name: `law-nutriai-prod` → Click **"OK"** |
3. Click **"Review + create"** → **"Create"**

### Connect to App Service

4. After deployment, go to the Application Insights resource
5. On the **Overview** page, copy the **Connection String**
6. Go to App Service → **"Environment variables"** → Add:

| Name | Value |
|------|-------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | *Paste the connection string* |

7. Click **"Apply"** → **"Confirm"**

### Connect to Function App

8. Go to Function App → **"Environment variables"** → Add the same connection string:

| Name | Value |
|------|-------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | *Same connection string* |

9. Click **"Apply"** → **"Confirm"**

---

## Step 12: Configure Database Firewall for App Service

Ensure your App Service can reach the PostgreSQL database.

1. Go to your PostgreSQL Flexible Server (`psql-nutriai-prod`)
2. Left menu → **"Settings"** → **"Networking"**
3. Under **Firewall rules**, verify:
   - ✅ **"Allow public access from any Azure service within Azure to this server"** is checked
4. If you need to add specific IPs:
   - Click **"+ Add current client IP address"** for portal access
   - Add the App Service outbound IPs (found in App Service → **"Properties"** → **"Outbound IP addresses"**)
5. Click **"Save"**

---

## Step 13: Verify Deployment

### Check App Service Logs

1. Go to App Service → Left menu → **"Monitoring"** → **"Log stream"**
2. Wait for logs to appear — you should see Gunicorn startup messages
3. If you see errors, check:
   - **"Diagnose and solve problems"** in the left menu
   - **"Deployment Center"** → **"Logs"** tab for container pull issues

### Test the Application

4. Open your browser and navigate to:
   - **Landing page**: `https://app-nutriai-prod.azurewebsites.net/`
   - **Login page**: `https://app-nutriai-prod.azurewebsites.net/auth/login`
   - **Register**: `https://app-nutriai-prod.azurewebsites.net/auth/register`
   - **Help page**: `https://app-nutriai-prod.azurewebsites.net/help`

5. Register a test user and verify:
   - ✅ Dashboard loads with stats
   - ✅ Document upload works (drag-and-drop)
   - ✅ Profile page loads
   - ✅ Health tracker renders with charts
   - ✅ Microsoft SSO button redirects properly (if Entra ID is configured)

### Check Function App

6. Go to Function App → **"Functions"** in the left menu
7. Verify both functions are listed:
   - `process_documents` (HTTP trigger)
   - `send_notifications` (Timer trigger)
8. Click on each → **"Monitor"** to see execution history

---

## Step 14: Backups & Alerts (Recommended)

### Enable Database Backup

1. Go to PostgreSQL Server → **"Settings"** → **"Backup"**
2. Verify:
   - Backup retention period: **14 days** (increase if needed)
   - Geo-redundant backup: Enable for production

### Set Up Alerts

3. Go to App Service → Left menu → **"Monitoring"** → **"Alerts"**
4. Click **"+ Create"** → **"Alert rule"**
5. **Condition**: Select **"CPU Percentage"** → Set threshold to **80%**
6. **Actions**: Create an Action Group → Add your email for notifications
7. **Details**: Name the rule `High CPU Alert`
8. Click **"Review + create"** → **"Create"**

### Enable Diagnostic Logging

9. Go to App Service → **"Monitoring"** → **"App Service logs"**
10. Configure:
    | Setting | Value |
    |---------|-------|
    | Application logging (Filesystem) | **On** |
    | Level | **Information** |
    | Detailed error messages | **On** |
    | Failed request tracing | **On** |
    | Web server logging | **File System**, Retention: **7 days** |
11. Click **"Save"**

---

## 🔒 Security Checklist

After deployment, verify all items:

- [ ] `SECRET_KEY` is a strong random value (not the default)
- [ ] All API keys stored in Azure Key Vault
- [ ] PostgreSQL is **not** publicly accessible (or restricted to Azure services only)
- [ ] Storage account has **no public blob access**
- [ ] **HTTPS Only** enabled on App Service
- [ ] **Managed Identity** enabled for Key Vault access
- [ ] Entra ID app registration has minimal permissions (User.Read only)
- [ ] Application Insights monitoring is active
- [ ] Database backup retention is at least 14 days
- [ ] Docker container runs as non-root user
- [ ] TLS 1.2 minimum enforced on all services

---

## 💰 Cost Estimation

| Service | SKU / Tier | Estimated Monthly Cost (USD) |
|---------|-----------|------------------------------|
| App Service Plan | Basic B2 (Linux) | ~$55 |
| PostgreSQL Flexible Server | Burstable B2s | ~$25 |
| Azure Storage | Standard LRS | ~$5 |
| Azure OpenAI (GPT-4) | Standard | ~$20–100 (usage-based) |
| Document Intelligence | Standard S0 | ~$50 (usage-based) |
| Function App | Consumption | ~$0–5 |
| Key Vault | Standard | ~$1 |
| Application Insights | Pay-as-you-go | ~$5–15 |
| Container Registry | Basic | ~$5 |
| **Total (Estimated)** | | **~$165–260/month** |

> [!TIP]
> **Save money**: Use [Azure Reservations](https://azure.microsoft.com/en-us/pricing/reservations/) for 1-year or 3-year commitments to save 30–50% on compute. For development/testing, use the **Free tier** App Service Plan (F1) and **Burstable B1ms** PostgreSQL.

---

## 🔧 Troubleshooting

| Issue | Where to Check | Solution |
|-------|---------------|----------|
| App won't start | App Service → Deployment Center → Logs | Verify `WEBSITES_PORT=8000` is set; check Docker image |
| "502 Bad Gateway" | App Service → Diagnose and solve problems | Container may have crashed — check Log stream |
| Database connection refused | PostgreSQL → Networking | Add App Service outbound IPs to firewall rules |
| OCR fails on upload | Function App → Functions → Monitor | Verify Document Intelligence key and endpoint |
| SSO redirect error | Entra ID → App registrations → Redirect URIs | Ensure redirect URI matches exactly |
| Function App not triggered | Function App → Functions → Monitor | Check function.json bindings and app settings |
| Blob upload fails | Storage Account → Access keys | Verify connection string is correct |
| "No module named..." | App Service → Log stream | Ensure all dependencies are in requirements.txt |

### Viewing Live Logs

1. **App Service**: Go to → **"Monitoring"** → **"Log stream"**
2. **Function App**: Go to → **"Functions"** → Click function → **"Monitor"**
3. **Application Insights**: Go to → **"Investigate"** → **"Failures"** or **"Performance"**

---

## 🔄 Updating the Application

When you make code changes and want to redeploy:

1. **Build and push new Docker image**:
   ```bash
   docker build -t nutriai-health-portal:latest .
   docker tag nutriai-health-portal:latest acrnutriaiprod.azurecr.io/nutriai-health-portal:v2
   docker push acrnutriaiprod.azurecr.io/nutriai-health-portal:v2
   ```

2. **Update App Service**:
   - Go to App Service → **"Deployment Center"**
   - Update the **Tag** to `v2`
   - Click **"Save"**
   - Or: Go to **"Overview"** → Click **"Restart"** (if using `latest` tag)

3. **Update Function App**:
   ```bash
   cd function_app
   func azure functionapp publish func-nutriai-prod --python
   ```

---

## 📋 Complete Environment Variables Summary

### App Service (`app-nutriai-prod`)

| Variable | Source |
|----------|--------|
| `SECRET_KEY` | Self-generated random string |
| `DATABASE_URL` | Step 4 (PostgreSQL connection string) |
| `AZURE_STORAGE_CONNECTION_STRING` | Step 3 (Storage access keys) |
| `AZURE_STORAGE_CONTAINER_NAME` | `health-documents` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Step 6 (DI Keys and Endpoint) |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Step 6 (DI Keys and Endpoint) |
| `AZURE_OPENAI_ENDPOINT` | Step 5 (OpenAI Keys and Endpoint) |
| `AZURE_OPENAI_KEY` | Step 5 (OpenAI Keys and Endpoint) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4` |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` |
| `AZURE_KEYVAULT_URL` | Step 2 (Key Vault URI) |
| `ENTRA_CLIENT_ID` | Step 10 (App registration) |
| `ENTRA_CLIENT_SECRET` | Step 10 (App registration) |
| `ENTRA_TENANT_ID` | Step 10 (App registration) |
| `ENTRA_REDIRECT_URI` | `https://app-nutriai-prod.azurewebsites.net/auth/callback` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Step 11 (Application Insights) |
| `FUNCTION_APP_URL` | Step 9 (Function App URL) |
| `FUNCTION_APP_KEY` | Step 9 (Function key) |
| `WEBSITES_PORT` | `8000` |

### Function App (`func-nutriai-prod`)

| Variable | Source |
|----------|--------|
| `DATABASE_URL` | Step 4 |
| `AZURE_STORAGE_CONNECTION_STRING` | Step 3 |
| `AZURE_STORAGE_CONTAINER_NAME` | `health-documents` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Step 6 |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Step 6 |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Step 11 |

---

<p align="center">
  📖 For application details, see the <a href="README.md">README</a>
</p>
