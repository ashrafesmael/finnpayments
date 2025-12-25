# finnverify

**AML Screening Platform** - Automated Anti-Money Laundering compliance screening with real-time risk assessment.

![finnverify](https://img.shields.io/badge/version-1.0.0-teal) ![License](https://img.shields.io/badge/license-Proprietary-blue)

## Overview

finnverify is a comprehensive AML (Anti-Money Laundering) screening platform that provides:

- **Sanctions Screening** - Real-time checks against global sanctions lists (OFAC, UN, EU, etc.)
- **PEP Screening** - Politically Exposed Person identification
- **Adverse Media Monitoring** - AI-powered news and media analysis
- **Jurisdiction Risk Assessment** - Live FATF blacklist/greylist checks
- **Document Processing** - OCR-based KYC document extraction

## Risk Scoring

| Risk Category | Weight | Source |
|--------------|--------|--------|
| Sanctions | 85% | Dilisense / World Check One |
| PEP | 30% | Dilisense / World Check One |
| Adverse Media | 20% | LLM-evaluated web search |
| Jurisdiction | 20% | FATF Live Check |

### Risk Levels

- **LOW** (< 15): Proceed with business
- **MEDIUM** (15-39): Enhanced Due Diligence required
- **HIGH** (40-74): Escalate for review, do not proceed
- **CRITICAL** (≥ 75): Immediate FIU reporting required

## Features

- ✅ Real-time screening against multiple databases
- ✅ PDF report generation with detailed findings
- ✅ Name matching with fuzzy logic (75% threshold)
- ✅ FATF jurisdiction risk (live web check)
- ✅ LLM-powered adverse media analysis
- ✅ Document upload with OCR extraction
- ✅ Manual screening interface
- ✅ User authentication system

## Tech Stack

**Backend:**
- Python 3.12 / FastAPI
- SQLite database
- Groq LLM (Llama 3.3 70B)
- OCR.space for document processing

**Frontend:**
- React 18 + Vite
- Tailwind CSS

**Screening Providers:**
- Dilisense AML Database
- World Check One (LSEG/Refinitiv)
- SerpAPI (adverse media search)

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+
- API Keys for: Dilisense, World Check One, Groq, SerpAPI, OCR.space

### Setup
```bash
# Clone repository
git clone https://github.com/hosnibelfeki/finnverify.git
cd finnverify

# Backend setup
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
npm run build
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
./start-all.sh
```

### Environment Variables
```env
DILISENSE_API_KEY=your_key
WORLDCHECK_API_KEY=your_key
WORLDCHECK_API_SECRET=your_secret
GROQ_API_KEY=your_key
SERPAPI_KEY=your_key
OCR_SPACE_API_KEY=your_key
```

## Usage

### Web Interface

Access the platform at `https://your-domain.com`

- **Manual Screening**: Enter entity name, type, and country
- **Document Upload**: Upload KYC documents for automated extraction and screening

### API Endpoints
```
POST /api/analyze/manual    - Manual entity screening
POST /api/analyze/upload    - Document upload and screening
GET  /api/report/{id}       - Download PDF report
GET  /api/health            - Health check
```

## Deployment

### Production (nginx + systemd)
```bash
# Configure nginx
sudo cp nginx/finnverify /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/finnverify /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup SSL
sudo certbot --nginx -d screen.finnverify.com

# Start services
sudo systemctl enable finnverify-backend finnverify-frontend
sudo systemctl start finnverify-backend finnverify-frontend
```

## License

Proprietary - © 2025 Finnpact Ltd. All rights reserved.

## Support

For support, contact: support@finnverify.com
