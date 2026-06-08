# 🥗 NutriAI Health Portal

**AI-Powered Personalized Diet Planning Platform**

NutriAI Health Portal is a cloud-native health technology platform that uses GPT-4 to analyze medical documents and generate personalized, allergy-safe diet plans. Built with a microservices architecture on Azure, it features React frontend, FastAPI backend services, and comprehensive infrastructure-as-code with Terraform.

[![Azure](https://img.shields.io/badge/Cloud-Azure-0078D4?logo=microsoftazure)](https://azure.microsoft.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react)](https://react.dev)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform)](https://terraform.io)
[![GPT-4](https://img.shields.io/badge/AI-GPT--4-412991?logo=openai)](https://openai.com)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED?logo=docker)](https://docker.com)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AZURE CLOUD                              │
│                                                                 │
│  ┌─────────────┐    ┌──────────────────────────────────────┐   │
│  │   React SPA  │───▶│         API Gateway (:8000)          │   │
│  │  (Nginx/SWA) │    │   JWT validation + request routing   │   │
│  └─────────────┘    └──────────┬───────────────────────────┘   │
│                                │                                │
│         ┌──────────────────────┼──────────────────────┐        │
│         ▼                      ▼                      ▼        │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │Auth Service  │  │Document Service  │  │ Diet Service     │  │
│  │   (:8001)    │  │   (:8002)        │  │   (:8003)        │  │
│  │ JWT, SSO,    │  │ Upload, OCR      │  │ GPT-4, PDF,      │  │
│  │ Registration │  │ status polling   │  │ Service Bus      │  │
│  └──────────────┘  └──────────────────┘  └──────────────────┘  │
│         ▼                      ▼                      ▼        │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │Health Svc   │  │Notification Svc  │  │Profile Service   │  │
│  │   (:8004)    │  │   (:8005)        │  │   (:8006)        │  │
│  │ Metrics,     │  │ Service Bus      │  │ User, Allergies  │  │
│  │ Chart.js     │  │ consumer, email  │  │ Medical info     │  │
│  └──────────────┘  └──────────────────┘  └──────────────────┘  │
│         ▼                                                       │
│  ┌──────────────┐                                              │
│  │Admin Service │                                              │
│  │   (:8007)    │     ┌──────────────────────────────────┐    │
│  │ Dashboard,   │     │     Shared PostgreSQL Database    │    │
│  │ User mgmt    │     │     (Azure Flexible Server)      │    │
│  └──────────────┘     └──────────────────────────────────┘    │
│                                                                 │
│  ┌───────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐ │
│  │Azure Blob │ │Azure OpenAI│ │Service Bus │ │Function App │ │
│  │ Storage   │ │  (GPT-4)   │ │(Meal Rmdr) │ │  (OCR)      │ │
│  └───────────┘ └────────────┘ └────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Diet Planning** | GPT-4 analyzes medical documents and generates personalized weekly meal plans with 3-attempt validation retry |
| 📄 **Document OCR** | Azure Document Intelligence extracts text from PDFs and images with status polling |
| 🛡️ **Allergy Protection** | Patient allergies are always included in AI prompts; foods containing allergens flagged in every plan |
| 📊 **Health Tracking** | Track weight, blood sugar, blood pressure with interactive Chart.js visualizations |
| 🔔 **Meal Reminders** | Service Bus publishes 28 scheduled email reminders (4 meals × 7 days) per diet plan |
| 🔐 **Dual Authentication** | Local JWT + Microsoft Entra ID SSO with cookie-based tokens |
| 📋 **PDF Export** | Professional diet plan PDFs generated with ReportLab |
| 👑 **Admin Panel** | User management, system stats, document oversight |
| 🏥 **HIPAA-Ready** | VNet isolation, Key Vault secrets, encrypted storage |

## 🛠️ Tech Stack

### Backend (8 Microservices)
- **Language**: Python 3.11
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 16 (shared, Azure Flexible Server)
- **ORM**: SQLAlchemy 2.0
- **Auth**: python-jose (JWT), passlib (bcrypt), msal (Entra ID)
- **AI**: Azure OpenAI SDK (GPT-4 with JSON mode)
- **PDF**: ReportLab
- **Messaging**: Azure Service Bus
- **Storage**: Azure Blob Storage

### Frontend
- **Framework**: React 18 + Vite 6
- **Routing**: React Router v6
- **State**: Context API + useAuth hook
- **HTTP**: Axios (withCredentials for JWT cookies)
- **Charts**: Chart.js + react-chartjs-2
- **Animations**: Framer Motion
- **Drag & Drop**: react-dropzone
- **Styling**: Bootstrap 5 + Custom CSS (identical to original design)

### Infrastructure
- **Cloud**: Microsoft Azure
- **IaC**: Terraform (15 modules)
- **Containers**: Docker + Docker Compose
- **Process Mgmt**: Supervisord (single-container backend)
- **Reverse Proxy**: Nginx (frontend)
- **CI/CD**: GitHub Actions (planned)

## 📁 Project Structure

```
cloud_project/
├── services/                    # 8 Backend Microservices
│   ├── api-gateway/             # Port 8000 - JWT validation + routing
│   ├── auth-service/            # Port 8001 - Login, Register, SSO
│   ├── document-service/        # Port 8002 - Upload, OCR, preview
│   ├── diet-service/            # Port 8003 - GPT-4, PDF, Service Bus
│   ├── health-service/          # Port 8004 - Health/meal logging
│   ├── notification-service/    # Port 8005 - Service Bus consumer, email
│   ├── profile-service/         # Port 8006 - Profile, allergies
│   └── admin-service/           # Port 8007 - Admin dashboard
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── api/                 # Axios client
│   │   ├── context/             # AuthContext
│   │   ├── hooks/               # useAuth
│   │   ├── components/          # Navbar, Footer, ProtectedRoute, etc.
│   │   ├── pages/               # 14 pages
│   │   └── styles/              # CSS (identical to original)
│   ├── nginx.conf               # Production reverse proxy
│   ├── Dockerfile               # Multi-stage build
│   └── package.json
├── terraform/                   # Infrastructure as Code
│   ├── main.tf                  # Provider configuration
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values
│   ├── modules.tf               # Module composition
│   └── modules/                 # 15 Terraform modules
│       ├── resource_group/
│       ├── vnet/
│       ├── key_vault/
│       ├── postgresql/
│       ├── storage/
│       ├── container_registry/
│       ├── app_service_plan/
│       ├── app_service/
│       ├── static_web_app/
│       ├── openai/
│       ├── service_bus/
│       ├── function_app/
│       ├── monitoring/
│       ├── alerts/
│       └── entra_id/
├── Dockerfile.backend           # All services via supervisord
├── supervisord.conf             # Process management
├── docker-compose.yml           # Local development (10 services)
├── DEPLOYMENT.md                # Full deployment guide
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Local Development with Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/nutriai-health-portal.git
cd nutriai-health-portal

# Create .env file with your secrets
cp .env.example .env
# Edit .env with your Azure credentials

# Start all services
docker compose up --build

# Frontend: http://localhost:3000
# API Gateway: http://localhost:8000
```

### Local Development (Without Docker)

```bash
# Backend: Start each service
cd services/auth-service
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## 🔒 Security Features

- **JWT Authentication** with HttpOnly cookies
- **Microsoft Entra ID** SSO integration
- **Azure Key Vault** for all secrets
- **VNet Integration** for backend-database communication
- **Private DNS Zones** for PostgreSQL
- **TLS 1.2+** enforced on all connections
- **CORS** configured per-service
- **Input Validation** on all API endpoints
- **Allergy Safety** - AI prompts always include patient allergies

## 📖 Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Full deployment guide with Azure setup, Terraform, and CI/CD
- **[API Documentation](http://localhost:8000/docs)** — Auto-generated FastAPI Swagger docs (per service)

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
  <b>Built with ❤️ for better health outcomes</b><br>
  <sub>NutriAI Health Portal © 2026</sub>
</div>
