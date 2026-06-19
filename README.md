# NutriAI Health Portal

NutriAI Health Portal is an enterprise-grade, cloud-native healthcare platform designed to automate patient document processing, track real-time health vitals, and generate personalized, AI-driven diet plans.

---

## 1. Problem Statement

Modern healthcare portals are often fragmented, requiring manual tracking of patient vitals and manual entry of medical lab reports. In addition:
* **Manual Data Entry Errors:** Transcribing complex medical PDFs and test results into dashboards manually is slow and error-prone.
* **Lack of Intelligent Personalization:** General health plans do not automatically adapt to a patient’s specific blood metrics, target vitals, allergies, food preferences, and historical medical conditions.
* **Security & Administration Gaps:** Lacking a secure role-based administrative layer to toggle user access, audit platform-wide logs, and verify document legitimacy leads to vulnerability.
* **Inefficient Scheduling:** Managing meal reminder triggers and notification pipelines asynchronously at scale requires complex queue structures.

---

## 2. The Solution

NutriAI solves these challenges by combining a microservice architecture with Microsoft Azure cloud capabilities:
* **Automated Document Intelligence (OCR):** Patients upload medical reports, which are parsed instantly to update dashboard health indicators using Azure Document Intelligence.
* **AI-Guided Document Validation:** Employs AI verification (with rule-based fallback) to only accept legitimate lab reports or prescriptions, preventing invalid file uploads.
* **Personalized AI-Guided Nutrition:** Generates tailored, safe weekly dietary schedules incorporating current lab results, chosen food categories (e.g. Vegetarian, Vegan), and historical medical history (previous diseases) using Azure OpenAI (GPT-4).
* **Decoupled Architecture with AGIC Routing:** Bypasses direct frontend-to-backend routing in favor of Azure Application Gateway Ingress Controller (AGIC), separating concerns and load-balancing traffic via auto-scaled pods (HPAs).
* **Asynchronous Alert Routing:** Schedules and fires reminders using a decoupled pub/sub message pattern via Azure Service Bus.

---

## 3. Key Features

1. **Patient SSO & Authentication:** Secure enrollment and login with Microsoft Entra ID support.
2. **AI Document Validation:** Validates that uploaded documents are indeed lab reports or prescriptions; otherwise, rejects them with a soft invalid document message.
3. **Automated Lab OCR Parser:** Instant PDF/image extraction of vitals and lab numbers.
4. **Interactive Vitals Tracker:** Health charts monitoring Weight, Blood Pressure, Heart Rate, Blood Sugar, and Height.
5. **AI Profile-Tailored Diet Planner:** GPT-4-powered weekly dietary schedule generator that incorporates past medical conditions (e.g. diabetes, hypertension) and dietary preferences (e.g., vegan, vegetarian).
6. **Decoupled Email Reminders:** Scheduled email notifications triggered automatically via message queues.
7. **Unified Administrator Dashboard:** Platform monitoring, database tracking, user listing, and user account active status toggles.
8. **Cloud-Scale Ingress & HPA:** Distributed microservices routed by AGIC and auto-scaled dynamically based on load (Horizontal Pod Autoscalers).

---

## 4. Microservices Directory

All services run inside their own containers and communicate over a bridge network in local development and via ClusterIP services in Kubernetes:

| Service Name | Folder Path | Port | Role / Functionality | Downstream Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **`frontend`** | `/frontend` | `80` (Internal)<br>`3000` (Local Host) | React SPA served by Nginx. Loaded by browser; communicates with backend via AGIC ingress routing. | `api-gateway` |
| **`api-gateway`** | `/services/api-gateway` | `8000` | Reverse Proxy. Validates JWT auth cookies, attaches context headers (`X-User-ID`, `X-User-Role`), strips `/api` prefix, and routes to microservices. | All backend microservices |
| **`auth-service`** | `/services/auth-service` | `8001` | Manages user registration, password hashing, JWT creation, and Entra ID SSO callbacks. | `postgres` |
| **`document-service`** | `/services/document-service` | `8002` | Uploads reports to storage, validates document types via AI, sends to OCR, and maps structured metrics. | `postgres`, Azure Storage, Azure Document Intelligence |
| **`diet-service`** | `/services/diet-service` | `8003` | Interfaces with OpenAI (GPT-4) to draft diet plans incorporating patient history/preferences, and publishes reminders to Service Bus. | `postgres`, Azure OpenAI, Azure Service Bus |
| **`health-service`** | `/services/health-service` | `8004` | Logs, updates, and fetches patient health vitals (such as blood pressure, heart rate, weight, and blood sugar). | `postgres` |
| **`notification-service`** | `/services/notification-service` | `8005` | Listens to Service Bus subscription, processes events, and relays emails via SMTP. | `postgres`, Azure Service Bus, SMTP Server |
| **`profile-service`** | `/services/profile-service` | `8006` | Handles user account profile data, medical history, dietary preferences, and food allergies. | `postgres` |
| **`admin-service`** | `/services/admin-service` | `8007` | Allows administrators to audit system status, view registration lists, and toggle user active states. | `postgres` |
| **`postgres`** | *Infrastructure* | `5432` | Shared relational database storing auth records, profile structures, vitals, and diet logs. | None |
| **`redis`** | *Infrastructure* | `6379` | Fast memory store used for session tokens and intermediate caching. | None |

---

## 5. System Architecture & Flow

```
                     ┌──────────────────┐
                     │   User Browser   │
                     └────────┬─────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │    AGIC Ingress Controller   │
               └──────┬────────────────┬──────┘
       HTTP Routes    │                │ HTTP Routes
       (e.g., /)      │                │ (e.g., /api/*, /admin/*)
                      ▼                ▼
             ┌──────────────┐ ┌────────────────┐
             │   Frontend   │ │  api-gateway   │
             │  (Port 80)   │ │  (Port 8000)   │
             └──────────────┘ └────────┬───────┘
                                       │ Proxies & decorates
                                       │ with X-User-ID headers
                                       ▼
      ┌──────────────┬─────────┬───────┴─┬──────────────┬──────────────┐
      │              │         │         │              │              │
      ▼              ▼         ▼         ▼              ▼              ▼
 ┌───────┐      ┌────────┐┌───────┐ ┌────────┐     ┌───────┐      ┌───────┐
 │ Auth  │      │Document││ Diet  │ │ Health │     │Profile│      │ Admin │
 │(8001) │      │ (8002) ││(8003) │ │ (8004) │     │(8006) │      │(8007) │
 └───┬───┘      └───┬────┘└───┬───┘ └───┬────┘     └───┬───┘      └───┬───┘
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

// Ingress Routing
Ingress [label: "AGIC Ingress Controller", icon: tencent-cloud, color: purple]

// Gateways
ApiGateway [label: "API Gateway (Port 8000)", icon: gateway, color: purple]

// Databases Group (Infrastructure)
group Infrastructure {
  Redis [label: "Redis Cache (Port 6379)", icon: database, color: orange]
  Postgres [label: "PostgreSQL (Port 5432)", icon: database, color: orange]
}

// Microservices Group
// Ordered logically from top to bottom to optimize layout and prevent crossed lines:
// - Top services connect exclusively to PostgreSQL / Redis
// - Middle service (Document) connects to file/OCR cloud storage
// - Bottom services (Diet, Notification) connect to AI, Service Bus, and SMTP
group Microservices {
  AuthService [label: "Auth Service (Port 8001)", icon: lock, color: green]
  ProfileService [label: "Profile Service (Port 8006)", icon: user, color: green]
  HealthService [label: "Health Service (Port 8004)", icon: heart, color: green]
  AdminService [label: "Admin Service (Port 8007)", icon: settings, color: green]
  DocumentService [label: "Document Service (Port 8002)", icon: document, color: green]
  DietService [label: "Diet Service (Port 8003)", icon: list, color: green]
  NotificationService [label: "Notification Service (Port 8005)", icon: mail, color: green]
}

// External Cloud Services Group
// Aligned vertically to match the microservices on their left
group AzureCloudServices {
  BlobStorage [label: "Azure Blob Storage", icon: folder, color: light-blue]
  DocIntelligence [label: "Azure Document Intelligence", icon: cpu, color: light-blue]
  OpenAI [label: "Azure OpenAI (GPT-4)", icon: message-square, color: light-blue]
  ServiceBus [label: "Azure Service Bus (Topic)", icon: send, color: light-blue]
}

// SMTP Relay (Placed at the bottom for the email delivery loop)
SmtpServer [label: "SMTP Server", icon: mail, color: gray]

// Architecture Connections
User > Ingress: "Access UI / Send Requests"
Ingress > Frontend: "Route UI requests (/)"
Ingress > ApiGateway: "Route API requests (/api/*, /admin/*)"

// Gateway Routing & Cache Connection
ApiGateway > Redis: "Cache JWT Sessions"
ApiGateway > AuthService: "Auth Actions (/auth)"
ApiGateway > ProfileService: "Patient Profile (/profile)"
ApiGateway > HealthService: "Log Vitals (/health-tracker)"
ApiGateway > AdminService: "Platform Audit (/admin)"
ApiGateway > DocumentService: "Upload Docs (/documents)"
ApiGateway > DietService: "Diet Planner (/diet-plan)"

// DB Integrations
AuthService > Postgres: "Read/Write Users"
ProfileService > Postgres: "Update Profile"
HealthService > Postgres: "Store Vitals"
AdminService > Postgres: "Audit Logs"
DocumentService > Postgres: "Save Metrics"
DietService > Postgres: "Read Vitals/Write Plans"

// Cloud Services Integrations
DocumentService > BlobStorage: "1. Upload PDF"
DocumentService > DocIntelligence: "2. Analyze Document"
DietService > OpenAI: "1. Generate Diet Plan via AI"
DietService > ServiceBus: "2. Publish Meal Reminders"

// Message Consumer & Email Relay Loop
ServiceBus > NotificationService: "3. Pull Reminders (Asynchronous)"
NotificationService > SmtpServer: "4. Relay Email Alerts"
SmtpServer > User: "5. Deliver Meal Reminder"
```
