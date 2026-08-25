# ControlSphere — Enterprise Cybersecurity GRC Platform

**ControlSphere** is an AI-assisted, enterprise-grade cybersecurity Governance, Risk & Compliance (GRC) platform. It connects compliance frameworks, security controls, evidence management, control assessments, audit findings, cybersecurity risk registers, remediation tracking, verification, and audit readiness into one deterministic, traceable workflow.

```
Framework ➔ Control ➔ Evidence ➔ Assessment ➔ Finding ➔ Risk ➔ Remediation ➔ Verification ➔ Audit Readiness
```

---

## 🏛️ System Architecture

ControlSphere employs a clean layered architecture with deterministic backend calculations and strict tenant isolation:

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons, React Query, React Hook Form, Zod.
- **Backend**: Python 3.12, FastAPI (REST + OpenAPI), Pydantic v2, SQLAlchemy 2.0 (ORM), Alembic (Migrations).
- **Security & Cryptography**: Native Bcrypt password hashing, JWT (HMAC-SHA256) session tokens, server-enforced RBAC.
- **Data Persistence & Isolation**: PostgreSQL 15 with foreign-key constraints, tenant boundaries, and immutable audit logs.
- **Containerization & Orchestration**: Docker & Docker Compose for multi-container local development and deployment.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- **Python** >= 3.11
- **Node.js** >= 20 & npm
- **Docker** & **Docker Compose** (for containerized PostgreSQL)

### 2. Environment Setup
Copy the environment template:
```bash
cp .env.example .env
```

### 3. Running with Docker Compose
To launch PostgreSQL, the FastAPI Backend, and the React Frontend simultaneously:
```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:5173`
- Backend API Docs (Swagger): `http://localhost:8000/api/v1/docs`
- Health Check: `http://localhost:8000/health`

---

## 💻 Manual Local Development Setup

### Backend
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt

# Run Database Migrations
alembic upgrade head

# Seed Initial Demo Organization & Users
python -m app.db.init_db

# Start FastAPI Dev Server
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Automated Testing

ControlSphere includes a comprehensive automated test suite verifying security boundaries, authorization matrices, tenant isolation, and audit logging.

To run the backend test suite:
```bash
cd backend
python -m pytest tests -v
```

### Verified Test Matrix:
- `test_health.py`: Root `/health` and API `/api/v1/health` connectivity.
- `test_auth.py`: JWT generation, login verification, password hashing, and user profile retrieval.
- `test_rbac.py`: Server-side role enforcement (ADMIN, GRC_ANALYST, AUDITOR, VIEWER).
- `test_tenant_isolation.py`: Cross-tenant data isolation and IDOR prevention between organizations.
- `test_audit_logging.py`: Immutable audit record generation for authentication, resource modifications, and unauthorized access attempts.

---

## 👥 Demo Credentials

| Role | Email | Password | Tenant |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@apexfinancial.com` | `AdminPassword123!` | Apex Financial Services |
| **GRC Analyst** | `analyst@apexfinancial.com` | `AnalystPassword123!` | Apex Financial Services |
| **Auditor** | `auditor@apexfinancial.com` | `AuditorPassword123!` | Apex Financial Services |
| **Viewer** | `viewer@apexfinancial.com` | `ViewerPassword123!` | Apex Financial Services |
| **Secondary Tenant** | `admin@meridianhealth.com` | `MeridianAdmin123!` | Meridian Health Systems |

---

## 📂 Project Structure

```
ControlSphere/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/              # API router and versioned endpoints
│   │   │   └── v1/endpoints/ # Auth, Users, Organizations, AuditLogs, Health
│   │   ├── core/             # Configuration, Security, and RBAC permissions
│   │   ├── db/               # SQLAlchemy Session and DB initialization
│   │   ├── models/           # SQLAlchemy Data Models (Org, User, AuditLog)
│   │   ├── schemas/          # Pydantic v2 validation models
│   │   └── services/         # Business logic & repository services
│   ├── tests/                # Automated security & isolation test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Layout (Sidebar, Header) & UI primitives (Cards, Tables)
│   │   ├── context/          # Auth & Organization state context
│   │   ├── lib/              # Axios API client
│   │   ├── pages/            # Login, Dashboard, User Management, Audit Explorer
│   │   └── types/            # TypeScript domain interfaces
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
├── CONTROLSPHERE.md
└── README.md
```