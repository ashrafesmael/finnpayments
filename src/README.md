# FinnPayments

**Invoice Processing & Accounting Entries**

---

## Overview

FinnPayments is an AI-powered invoice processing system that extracts data from uploaded invoices and automatically generates double-entry accounting journal entries. Built on the same architecture as FinnVerify (FastAPI + React/Vite), it provides:

- **Invoice OCR & Extraction** — Upload PDF/image invoices, extract vendor details, line items, amounts
- **AI Enhancement** — Groq LLM integration for intelligent data extraction and account code suggestion
- **Accounting Entries** — Auto-generate balanced journal entries following double-entry bookkeeping
- **Chart of Accounts** — Pre-configured for Mauritian property development (Mont Choisy Group)
- **Approval Workflow** — Draft → Pending Review → Approved → Posted → Paid
- **VAT Handling** — Mauritius 15% VAT with separate input/output tracking

## Architecture

```
finnpayments/
├── run.py                     # Entry point (uvicorn server)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment config template
├── start-all.sh              # Dev startup script
│
├── src/                      # Backend (FastAPI)
│   ├── api.py                # REST API endpoints
│   ├── models.py             # Pydantic data models
│   ├── database.py           # SQLAlchemy ORM + SQLite
│   ├── invoice_engine.py     # PDF extraction + AI processing
│   └── accounting_engine.py  # Journal entry generation
│
├── frontend/                 # Frontend (React + Vite + Tailwind)
│   ├── src/
│   │   ├── App.jsx           # Main application (all views)
│   │   ├── services/api.js   # API client
│   │   └── index.css         # Tailwind styles
│   └── package.json
│
├── deploy/                   # systemd service files
│   ├── finnpayments-backend.service
│   └── finnpayments-frontend.service
│
├── temp_uploads/             # Uploaded invoice files
├── logs/                     # Application logs
└── static/                   # Static assets
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) Groq API key for AI enhancement

### 1. Backend Setup

```bash
cd finnpayments

# Install Python dependencies
pip install -r requirements.txt --break-system-packages

# Copy and configure environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Start backend
python3 run.py
```

Backend runs at `http://localhost:8001`  
API docs at `http://localhost:8001/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3001`

### 3. Or use the combined startup

```bash
chmod +x start-all.sh
./start-all.sh
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/invoices/upload` | Upload & process invoice |
| `POST` | `/invoices/manual` | Create invoice manually |
| `GET` | `/invoices` | List invoices (filterable) |
| `GET` | `/invoices/{id}` | Invoice detail with entries |
| `PATCH` | `/invoices/{id}/status` | Update invoice status |
| `DELETE` | `/invoices/{id}` | Delete invoice |
| `GET` | `/accounting/entries` | List journal entries |
| `POST` | `/accounting/entries/{id}/post` | Post entry to GL |
| `POST` | `/accounting/entries/{id}/reverse` | Create reversing entry |
| `GET` | `/accounting/chart-of-accounts` | Chart of accounts |
| `GET` | `/accounting/suggest-account` | AI account suggestion |
| `GET` | `/dashboard/stats` | Dashboard statistics |

## Accounting Logic

### Supplier Invoice (AP)
```
Dr. Expense Account      (net amount)
Dr. VAT Input            (tax amount)
    Cr. Accounts Payable     (total amount)
```

### Client Invoice (AR)
```
Dr. Accounts Receivable  (total amount)
    Cr. Revenue Account      (net amount)
    Cr. VAT Output           (tax amount)
```

### Credit Note
Reverses the original entry pattern.

## Deployment (n8n-enhanced server)

```bash
# Copy service files
sudo cp deploy/finnpayments-backend.service /etc/systemd/system/
sudo cp deploy/finnpayments-frontend.service /etc/systemd/system/

# Set GROQ_API_KEY in service file
sudo nano /etc/systemd/system/finnpayments-backend.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable finnpayments-backend finnpayments-frontend
sudo systemctl start finnpayments-backend finnpayments-frontend

# Check status
sudo systemctl status finnpayments-backend
sudo systemctl status finnpayments-frontend
```

## Relationship to FinnVerify

FinnPayments shares FinnVerify's architecture:
- FastAPI backend with the same endpoint patterns
- React/Vite frontend with Tailwind CSS
- Groq LLM integration for AI enhancement
- SQLite database with SQLAlchemy ORM
- systemd service deployment on n8n-enhanced server

Both are part of the **Finn** product suite:
- **FinnVerify** — AML/KYC screening & compliance
- **FinnPayments** — Invoice processing & accounting entries

---

*Powered by Groq AI*
