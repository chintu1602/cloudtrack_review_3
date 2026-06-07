# 🌿 NutriAI Health Portal

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure](https://img.shields.io/badge/Azure-Cloud-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **AI-powered personalized diet planning for patients** — Upload medical documents, get intelligent dietary recommendations powered by Azure OpenAI GPT-4, and track your health journey over time.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Local Development](#-local-development)
- [API Routes](#-api-routes)
- [Authentication](#-authentication)
- [Azure Services](#-azure-services)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

NutriAI Health Portal is a comprehensive web application that enables patients to:
1. **Upload** medical documents (lab reports, prescriptions) securely to Azure Blob Storage
2. **Extract** content from documents using Azure Document Intelligence (OCR)
3. **Generate** personalized diet plans using Azure OpenAI GPT-4, considering patient allergies and medical history
4. **Track** health metrics (weight, blood sugar, blood pressure) and meals over time
5. **Visualize** health trends with interactive Chart.js dashboards

---

## ✨ Features

| Category | Features |
|----------|----------|
| 🔐 **Authentication** | Local JWT auth + Microsoft Entra ID SSO |
| 📄 **Documents** | Drag-and-drop upload, OCR processing, status tracking |
| 🥗 **Diet Plans** | AI-generated personalized meal plans with allergy awareness |
| 📊 **Health Tracking** | Weight, blood sugar, blood pressure charts with meal logging |
| 👤 **Profile** | Medical conditions, dietary preferences, food allergy management |
| 🔔 **Notifications** | Document processing alerts and system notifications |
| 🛡️ **Admin** | User management, system stats, document oversight |
| 📱 **Responsive** | Fully responsive Bootstrap 5 UI with modern animations |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0 |
| **Frontend** | Jinja2 Templates, Bootstrap 5.3, Chart.js 4.4 |
| **Database** | PostgreSQL 15 with Alembic migrations |
| **Auth** | JWT (python-jose) + MSAL (Microsoft Entra ID) |
| **Cloud Storage** | Azure Blob Storage |
| **OCR** | Azure Document Intelligence (prebuilt-read) |
| **AI** | Azure OpenAI GPT-4 |
| **Secrets** | Azure Key Vault |
| **Serverless** | Azure Functions (document processing & notifications) |
| **Monitoring** | Azure Application Insights |
| **Container** | Docker + Docker Compose |
| **Deployment** | Azure App Service, Azure Container Registry |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Browser                          │
│              (Bootstrap 5 + Chart.js + Custom JS)               │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────────────────┐
│                    Azure App Service                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FastAPI + Gunicorn/Uvicorn Workers                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐   │  │
│  │  │  Auth    │ │Documents │ │Diet Plans│ │  Health    │   │  │
│  │  │  Router  │ │  Router  │ │  Router  │ │  Tracker   │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘   │  │
│  │       │             │            │              │          │  │
│  │  ┌────▼─────────────▼────────────▼──────────────▼──────┐  │  │
│  │  │              Service Layer                          │  │  │
│  │  │  Auth │ Storage │ Doc Intelligence │ OpenAI │ Diet  │  │  │
│  │  └──────┴────┬─────┴────────┬─────────┴───┬────┴──────┘  │  │
│  └──────────────┼──────────────┼─────────────┼───────────────┘  │
└─────────────────┼──────────────┼─────────────┼──────────────────┘
                  │              │             │
    ┌─────────────▼──┐  ┌───────▼───────┐  ┌──▼──────────────┐
    │  PostgreSQL 15  │  │  Azure Blob   │  │  Azure OpenAI   │
    │  (SQLAlchemy)   │  │  Storage      │  │  (GPT-4)        │
    └────────────────┘  └───────────────┘  └─────────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │  Azure Function App         │
                  │  ┌────────────────────────┐ │
                  │  │ process_documents (HTTP)│ │
                  │  │ send_notifications     │ │
                  │  │              (Timer)    │ │
                  │  └───────────┬────────────┘ │
                  └──────────────┼──────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │  Azure Document Intelligence │
                  │  (prebuilt-read OCR)          │
                  └──────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)
- Azure subscription with required services provisioned

### Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/nutriai-health-portal.git
cd nutriai-health-portal

# 2. Create environment file
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Start services
docker-compose up -d

# 4. Access the application
open http://localhost:8000
```

### Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your database URL and Azure credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 💻 Local Development

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing secret | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage connection | ✅ |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document Intelligence endpoint | ✅ |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Document Intelligence API key | ✅ |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | ✅ |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | ✅ |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | GPT-4 deployment name | ✅ |
| `ENTRA_CLIENT_ID` | Entra ID app client ID | ❌ |
| `ENTRA_CLIENT_SECRET` | Entra ID app client secret | ❌ |
| `ENTRA_TENANT_ID` | Azure AD tenant ID | ❌ |

### Running with Hot Reload

```bash
uvicorn app.main:app --reload --port 8000
```

### Database Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## 🗺 API Routes

### Public Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Landing page |
| GET | `/help` | Help & FAQ page |

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/login` | Login form |
| POST | `/auth/login` | Process login |
| GET | `/auth/register` | Registration form |
| POST | `/auth/register` | Process registration |
| GET | `/auth/forgot-password` | Forgot password form |
| GET | `/auth/microsoft` | Entra ID SSO redirect |
| GET | `/auth/callback` | Entra ID callback |
| GET | `/auth/logout` | Logout |

### Protected Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | User dashboard |
| GET | `/documents` | Documents page |
| POST | `/documents/upload` | Upload document |
| GET | `/documents/{id}/status` | Check OCR status (JSON) |
| GET | `/documents/{id}/preview` | Preview document |
| DELETE | `/documents/{id}` | Delete document |
| GET | `/diet-plan` | Diet plan generator |
| POST | `/diet-plan/generate` | Generate AI diet plan |
| GET | `/diet-plan/history` | Plan history |
| GET | `/diet-plan/{id}` | View plan details |
| GET | `/diet-plan/{id}/pdf` | Download plan as PDF |
| GET | `/health-tracker` | Health tracker page |
| POST | `/health-tracker/log` | Log health data |
| POST | `/health-tracker/meal` | Log meal data |
| GET | `/health-tracker/data` | Chart data (JSON) |
| GET | `/profile` | User profile |
| POST | `/profile/update` | Update profile |
| POST | `/profile/medical` | Update medical info |
| POST | `/profile/allergy` | Add allergy |
| DELETE | `/profile/allergy/{id}` | Delete allergy |
| GET | `/notifications` | Notifications page |
| POST | `/notifications/{id}/read` | Mark as read |

### Admin Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin` | Admin dashboard |
| POST | `/admin/users/{id}/toggle` | Toggle user status |

---

## 🔐 Authentication

### Local Authentication
- Users register with email, username, and password
- Passwords hashed with **bcrypt** via passlib
- JWT tokens stored in **httponly cookies** (1-hour expiry)
- Token verification on every protected route via `get_current_user` dependency

### Microsoft Entra ID SSO
- MSAL library handles the OAuth 2.0 authorization code flow
- Users redirected to Microsoft login, then callback creates/updates local user record
- JWT cookie issued after successful SSO, seamlessly integrating with local auth

### Flow Diagram
```
User → Login Page → [Local Form / Microsoft SSO Button]
                         │                    │
                    POST /auth/login    GET /auth/microsoft
                         │                    │
                  Verify password        MSAL redirect to
                         │              Microsoft login
                         │                    │
                  Create JWT cookie    GET /auth/callback
                         │              (exchange code)
                         │                    │
                         └──── Set Cookie ────┘
                                   │
                            Redirect to /dashboard
```

---

## ☁️ Azure Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Blob Storage** | Secure medical document storage with SAS token access | Container: `health-documents` |
| **Document Intelligence** | OCR extraction from lab reports and prescriptions | Model: `prebuilt-read` |
| **OpenAI (GPT-4)** | AI diet plan generation with allergy awareness | JSON structured output |
| **Key Vault** | Secure secrets management | Optional in dev |
| **Function App** | Background document processing + cleanup | HTTP + Timer triggers |
| **Application Insights** | Monitoring, logging, and telemetry | OpenTelemetry SDK |

---

## 📁 Project Structure

```
nutriai-health-portal/
├── app/
│   ├── main.py                     # FastAPI entry point & core routes
│   ├── config.py                   # Pydantic Settings (env vars)
│   ├── database.py                 # SQLAlchemy engine & session
│   ├── dependencies.py             # Auth & role dependencies
│   ├── models/
│   │   ├── user.py                 # User, PatientProfile, FoodAllergy
│   │   ├── document.py             # Document (medical uploads)
│   │   ├── diet_plan.py            # DietPlan (AI-generated)
│   │   └── health_log.py           # HealthLog, MealLog
│   ├── schemas/
│   │   └── schemas.py              # Pydantic request/response models
│   ├── routers/
│   │   ├── auth.py                 # Login, register, SSO, logout
│   │   ├── documents.py            # Upload, OCR status, preview, delete
│   │   ├── diet_plans.py           # Generate, history, detail, PDF
│   │   ├── health_tracker.py       # Log health/meals, chart data
│   │   ├── profile.py              # Personal info, medical, allergies
│   │   ├── notifications.py        # Notification list, mark read
│   │   └── admin.py                # Admin dashboard, user management
│   ├── services/
│   │   ├── auth_service.py         # JWT, bcrypt, MSAL helpers
│   │   ├── azure_storage_service.py # Blob upload/download/SAS/delete
│   │   ├── document_intelligence_service.py  # OCR processing
│   │   ├── openai_service.py       # GPT-4 diet plan generation
│   │   └── diet_plan_service.py    # Orchestration service
│   └── templates/                  # Jinja2 HTML templates (15+ pages)
├── function_app/
│   ├── host.json                   # Function App config
│   ├── requirements.txt            # Function dependencies
│   ├── process_documents/          # HTTP trigger: OCR processing
│   └── send_notifications/         # Timer trigger: cleanup stuck docs
├── static/
│   ├── css/styles.css              # Custom CSS (600+ lines)
│   └── js/main.js                  # Client-side JavaScript
├── alembic/                        # Database migrations
├── tests/                          # Test suite
├── Dockerfile                      # Multi-stage production image
├── docker-compose.yml              # App + PostgreSQL services
├── startup.sh                      # Gunicorn startup script
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── README.md                       # This file
└── DEPLOYMENT.md                   # Azure deployment guide
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run with coverage
python -m pytest tests/ -v --cov=app --cov-report=html
```

Tests use mocked Azure services and an in-memory SQLite database for isolation.

---

## 🚢 Deployment

For comprehensive Azure deployment instructions including Azure CLI commands for all services, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

Quick deployment overview:
1. Create Azure Resource Group
2. Provision PostgreSQL Flexible Server
3. Set up Azure Blob Storage
4. Deploy Document Intelligence
5. Deploy Azure OpenAI with GPT-4
6. Create Azure Container Registry
7. Build and push Docker image
8. Deploy to Azure App Service
9. Deploy Azure Function App
10. Configure Entra ID app registration

---

## 🔒 Security

- ✅ **Password hashing** with bcrypt (passlib)
- ✅ **JWT tokens** in httponly, secure cookies
- ✅ **CORS** configured for allowed origins
- ✅ **CSRF protection** via SameSite cookies
- ✅ **Input validation** with Pydantic schemas
- ✅ **SQL injection prevention** via SQLAlchemy ORM
- ✅ **File type validation** on upload (PDF, JPEG, PNG only)
- ✅ **File size limits** (10MB max per document)
- ✅ **Non-root Docker** container user
- ✅ **Azure Key Vault** for secrets management
- ✅ **SAS tokens** with 1-hour expiry for blob access
- ✅ **Role-based access** (patient vs admin)
- ✅ **Owner-only** document/plan access checks

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with 💚 by the NutriAI Team
</p>
