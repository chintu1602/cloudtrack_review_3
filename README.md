# NutriAI Health Portal

NutriAI Health Portal is an enterprise-grade, cloud-native healthcare platform designed to automate patient document processing, track real-time health vitals, and generate personalized, AI-driven diet plans.

---

## 1. Problem Statement

Modern healthcare portals are often fragmented, requiring manual tracking of patient vitals and manual entry of medical lab reports. In addition:
* **Manual Data Entry Errors:** Transcribing complex medical PDFs and test results into dashboards manually is slow and error-prone.
* **Lack of Intelligent Personalization:** General health plans do not automatically adapt to a patient’s specific blood metrics, target vitals, and dietary restrictions.
* **Inefficient Scheduling:** Managing meal reminder triggers and notification pipelines asynchronously at scale requires complex queue structures.

---

## 2. The Solution

NutriAI solves these challenges by combining a microservice architecture with Microsoft Azure cloud capabilities:
* **Automated Document Intelligence (OCR):** Patients upload medical reports, which are parsed instantly to update dashboard health indicators using Azure Document Intelligence.
* **AI-Guided Nutrition:** Generates weekly dietary schedules based on target medical metrics and restrictions using Azure OpenAI (GPT-4).
* **Asynchronous Alert Routing:** Schedules and fires reminders using a decoupled pub/sub message pattern via Azure Service Bus.

---

## 3. Key Features

1. **Patient SSO & Authentication:** Secure enrollment and login with Microsoft Entra ID support.
2. **Automated Lab OCR Parser:** Instant PDF/image extraction of vitals and lab numbers.
3. **Interactive Vitals Tracker:** Health charts monitoring Weight, Blood Pressure, Heart Rate, and Blood Sugar.
4. **AI Diet Planner:** GPT-4 powered weekly dietary schedule generator.
5. **Decoupled Email Reminders:** Scheduled email notifications triggered automatically via message queues.
6. **Unified Administrator Dashboard:** Platform monitoring, database tracking, and global settings toggles.

---

## 4. Microservices Directory

All services run inside their own containers and communicate over a bridge network in local development and via ClusterIP services in Kubernetes:

| Service Name | Folder Path | Port | Role / Functionality | Downstream Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **`frontend`** | `/frontend` | `80` (Internal)<br>`3000` (Local Host) | React SPA served by Nginx. Proxies `/api` traffic internally to the API Gateway. | `gateway` |
| **`gateway`** | `/services/api-gateway` | `8000` | Reverse Proxy. Validates JWT auth cookies, attaches context headers, and routes to microservices. | All backend microservices |
| **`identity-service`** | `/services/auth-service` | `8001` | Manages user registration, password hashing, JWT creation, and Entra ID SSO callbacks. | `postgres` |
| **`ocr-service`** | `/services/document-service` | `8002` | Uploads reports to storage, sends them to OCR API, and returns structured metrics. | `postgres`, Azure Storage, Azure Document Intelligence |
| **`nutrition-service`** | `/services/diet-service` | `8003` | Interfaces with OpenAI to draft diet plans and schedules reminders by publishing to Service Bus. | `postgres`, Azure OpenAI, Azure Service Bus |
| **`vitals-service`** | `/services/health-service` | `8004` | Logs, updates, and fetches patient health vitals (such as blood pressure, heart rate, and weight). | `postgres` |
| **`email-service`** | `/services/notification-service` | `8005` | Listens to Service Bus subscription, processes events, and relays emails via SMTP/SendGrid. | `postgres`, Azure Service Bus, SMTP Server |
| **`patient-service`** | `/services/profile-service` | `8006` | Handles user account profile data, restrictions, and history storage. | `postgres` |
| **`admin-service`** | `/services/admin-service` | `8007` | Allows administrators to audit system status, adjust global parameters, and access logs. | `postgres` |
| **`postgres`** | *Infrastructure* | `5432` | Shared relational database storing auth records, profile structures, vitals, and diet logs. | None |
| **`redis`** | *Infrastructure* | `6379` | Fast memory store used for session tokens and intermediate caching. | None |

---

## 5. System Architecture & Flow

```
                     ┌──────────────────┐
                     │   User Browser   │
                     └────────┬─────────┘
                              │ Access Portal / API Requests
                              ▼
                ┌────────────────────────────┐
                │   Frontend Nginx (3000)    │
                └─────────────┬──────────────┘
                              │ Proxy /api/*
                              ▼
                ┌────────────────────────────┐
                │     API Gateway (8000)     │
                └─────────────┬──────────────┘
                              │
     ┌──────────────┬─────────┼─────────┬──────────────┬──────────────┐
     │              │         │         │              │              │
     ▼              ▼         ▼         ▼              ▼              ▼
 ┌───────┐      ┌───────┐ ┌───────┐ ┌───────┐      ┌───────┐      ┌───────┐
 │ Auth  │      │  OCR  │ │ Diet  │ │Vitals │      │Profile│      │ Admin │
 │(8001) │      │(8002) │ │(8003) │ │(8004) │      │(8006) │      │(8007) │
 └───┬───┘      └───┬───┘ └───┬───┘ └───┬───┘      └───┬───┘      └───┬───┘
     │              │         │         │              │              │
     └──────────────┼─────────┼─────────┴──────────────┼──────────────┤
                    │         │                        │              │
                    ▼         ▼                        ▼              ▼
               ┌────────────────────────────────────────────────────────┐
               │              Shared PostgreSQL DB (5432)               │
               └────────────────────────────────────────────────────────┘
```

---

## 6. Eraser.io Architecture Script

You can copy and paste the following script into [Eraser.io](https://www.eraser.io) to generate a dynamic visual architecture diagram for this application:

```text
// Users and Interface
User [icon: user, color: blue]
Frontend [label: "React SPA (Port 3000)", icon: chrome, color: blue]

// Gateways
Gateway [label: "API Gateway (Port 8000)", icon: gateway, color: purple]

// Microservices Group
group Microservices {
  AuthService [label: "Identity Service (Port 8001)", icon: lock, color: green]
  OcrService [label: "OCR Service (Port 8002)", icon: document, color: green]
  DietService [label: "Nutrition Service (Port 8003)", icon: list, color: green]
  VitalsService [label: "Vitals Service (Port 8004)", icon: heart, color: green]
  EmailService [label: "Email Service (Port 8005)", icon: mail, color: green]
  ProfileService [label: "Patient Service (Port 8006)", icon: user, color: green]
  AdminService [label: "Admin Service (Port 8007)", icon: settings, color: green]
}

// Databases Group
group Infrastructure {
  Postgres [label: "PostgreSQL (Port 5432)", icon: database, color: orange]
  Redis [label: "Redis Cache (Port 6379)", icon: database, color: orange]
}

// External Cloud Services Group
group AzureCloudServices {
  BlobStorage [label: "Azure Blob Storage", icon: folder, color: light-blue]
  DocIntelligence [label: "Azure Document Intelligence", icon: cpu, color: light-blue]
  OpenAI [label: "Azure OpenAI (GPT-4)", icon: message-square, color: light-blue]
  ServiceBus [label: "Azure Service Bus (Topic)", icon: send, color: light-blue]
}

// SMTP Relay
SmtpServer [label: "SMTP / SendGrid Server", icon: mail, color: gray]

// Architecture Connections
User > Frontend: "Access UI"
Frontend > Gateway: "Route API (/api/*)"

// Gateway Routing
Gateway > AuthService: "Auth Actions (/api/auth)"
Gateway > OcrService: "Upload Docs (/api/documents)"
Gateway > DietService: "Diet Planner (/api/diet-plan)"
Gateway > VitalsService: "Log Vitals (/api/health-tracker)"
Gateway > ProfileService: "Patient Profile (/api/profile)"
Gateway > AdminService: "Platform Audit (/api/admin)"

// DB Integrations
AuthService > Postgres: "Read/Write Users"
OcrService > Postgres: "Save Metrics"
DietService > Postgres: "Read Vitals/Write Plans"
VitalsService > Postgres: "Store Vitals"
ProfileService > Postgres: "Update Profile"
AdminService > Postgres: "Audit Logs"
Gateway > Redis: "Cache JWT Sessions"

// Cloud Services Integrations
OcrService > BlobStorage: "1. Upload PDF"
OcrService > DocIntelligence: "2. Analyze Document"
DietService > OpenAI: "1. Generate Diet Plan via AI"
DietService > ServiceBus: "2. Publish Meal Reminders"

// Message Consumer
ServiceBus > EmailService: "3. Pull Reminders (Asynchronous)"
EmailService > SmtpServer: "4. Relay Email Alerts"
SmtpServer > User: "5. Deliver Meal Reminder"
```
