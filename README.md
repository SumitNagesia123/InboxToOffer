---
title: InboxToOffer AI Platform
emoji: 📬
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# InboxToOffer

> AI-powered job email tracker that turns your Gmail inbox into a structured job search pipeline — for developers and job seekers who hate spreadsheets.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-104%20passing-brightgreen)

---

## Table of Contents
- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## About

Job seekers receive dozens of recruiter emails every week but have no structured way to track them. Manually copying details into spreadsheets is tedious, error-prone, and unsustainable.

**InboxToOffer** connects to your Gmail account via OAuth, automatically ingests job-related emails, scores each opportunity against your resume using an AI matching engine, and surfaces the best matches in a clean dashboard. It then tracks every application through the entire pipeline — from first email to final offer — so nothing falls through the cracks.

---

## Features

- **Gmail OAuth & IMAP Integration** — Secure incremental email sync using `X-GM-RAW` search filters with rate limiting and retry backoff
- **AI Triage Engine** — Automatically filters out non-job noise (e-commerce, promotions, alerts) before anything hits your database
- **Resume Matching & Scoring** — Multi-factor scoring (skills, experience level, semantic relevance) with natural-language explanations for every match
- **Application Pipeline** — Full lifecycle tracking across `Applied`, `Interviewing`, `Offer`, `Rejected`, and `Withdrawn` stages
- **Daily Digest** — Automated summaries of your top daily opportunities and upcoming interview schedules
- **Multi-tenant Auth** — JWT-based authentication with per-user data isolation and Fernet-encrypted OAuth token storage

---

## Tech Stack

**Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL  
**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS  
**AI/ML:** Sentence Transformers · scikit-learn  
**Auth & Security:** JWT · bcrypt · Fernet encryption · Google OAuth 2.0  
**DevOps:** Docker (multi-stage build)

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- A Google Cloud project with Gmail API enabled (for OAuth)

### Installation

```bash
git clone https://github.com/SumitNagesia123/InboxToOffer.git
cd InboxToOffer

# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Configuration

Copy `.env.example` to `.env` inside the `backend/` folder and fill in the values:

```
DATABASE_URL=postgresql://user:password@localhost:5432/inboxtooffer
SECRET_KEY=<64-character random hex string>
OAUTH_ENCRYPTION_KEY=<32-byte Fernet key>
ENVIRONMENT=development
GOOGLE_CLIENT_ID=<your Google OAuth client ID>
GOOGLE_CLIENT_SECRET=<your Google OAuth client secret>
```

> ⚠️ Never commit `.env` or any secrets. The `.gitignore` already excludes it.

Run database migrations:

```bash
cd backend
alembic upgrade head
```

---

## Usage

**Start the backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Start the frontend:**
```bash
cd frontend
npm run dev
# App runs at http://localhost:5173
```

**Or run with Docker (production):**
```bash
docker build -t inboxtooffer .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e SECRET_KEY=your_secret \
  -e OAUTH_ENCRYPTION_KEY=your_fernet_key \
  inboxtooffer
```

Once running: register an account → connect your Gmail via OAuth → upload your resume → let the AI find and score your job opportunities.

---

## Project Structure

```
InboxToOffer/
├── backend/
│   ├── app/
│   │   ├── api/            REST endpoints (auth, emails, matches, applications)
│   │   ├── core/           Config, security, encryption, logging
│   │   ├── database/       Session management and base model
│   │   ├── models/         SQLAlchemy ORM models
│   │   ├── schemas/        Pydantic request/response schemas
│   │   └── services/       Business logic (ingestion, triage, matching, digest)
│   ├── alembic/            Database migrations
│   ├── tests/              104 unit & integration tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/            API client
│       ├── components/     Reusable UI components
│       ├── context/        Auth and theme contexts
│       └── pages/          Dashboard, Emails, Matches, Applications, Analytics
├── docs/                   Architecture and database schema docs
├── Dockerfile              Multi-stage production container
└── README.md
```

---

## Testing

```bash
cd backend
pytest tests/ -v
```

104 tests covering auth, email ingestion, triage classification, job extraction, resume parsing, duplicate detection, matching engine, analytics, and API endpoints — all passing.

---

## Roadmap

- [x] Gmail OAuth & IMAP incremental sync
- [x] AI triage engine with reject logging
- [x] Resume upload and parsing
- [x] Multi-factor job-resume matching with explainability
- [x] Application pipeline (Applied → Offer)
- [x] Daily digest and analytics dashboard
- [x] Production Docker container
- [ ] Outlook / Yahoo Mail support
- [ ] Browser extension for one-click apply tracking
- [ ] Mobile-responsive PWA
- [ ] Interview scheduler with calendar integration

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push to your branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please follow conventional commit messages (`feat:`, `fix:`, `docs:`, etc.) and include tests for any new functionality.

---

## License

Distributed under the MIT License. See `LICENSE` for details.

---

## Contact

**Sumit Nagesia** · [GitHub @SumitNagesia123](https://github.com/SumitNagesia123) · [InboxToOffer](https://github.com/SumitNagesia123/InboxToOffer)

