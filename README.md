# InboxToOffer

> AI-powered job intelligence dashboard that turns your inbox into a structured job pipeline: it extracts job emails, removes duplicates, matches roles to your resume, and tracks applications.

[Live Demo](https://inbox-to-offer-frontend.vercel.app) · [API Docs](https://inboxtooffer.onrender.com/docs) · [Report a Bug](https://github.com/SumitNagesia123/InboxToOffer/issues)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![React](https://img.shields.io/badge/React-Vite-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [API Overview](#api-overview)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [License](#license)
- [Contact](#contact)

## Overview
Job hunting floods your inbox with alerts from many sources. InboxToOffer connects to Gmail, ingests those emails, uses AI to extract structured job data, filters duplicates, scores each role against your resume, and shows everything on one dashboard.

**Problem:** job emails are scattered, repetitive, and hard to compare.
**Solution:** one pipeline that ingests, parses, de-duplicates, matches, and tracks.

## Features
- **Gmail sync:** ingests job-related emails via Google OAuth.
- **AI parsing & triage:** extracts title, company, skills, and location while filtering out non-job noise.
- **Duplicate filtering:** merges repeated postings across sources using heuristic & semantic matching.
- **Resume matching:** compatibility score with a skill-by-skill breakdown and explainable scoring.
- **Application tracking:** pipeline view from applied to interview/offer.
- **Analytics and executive digest:** summary metrics and daily report.
- **Auth:** JWT-based login, registration, and secure token storage.

## Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL (Supabase) |
| AI / NLP | Sentence Transformers, TF-IDF / Cosine Similarity |
| Auth | JWT (PyJWT), bcrypt, Google OAuth 2.0 |
| Hosting | Vercel (frontend), Render (backend) |

## Architecture
```
Gmail ──► Backend (FastAPI) ──► AI parser ──► PostgreSQL (Supabase)
                 ▲                                   │
                 └──────────── React dashboard ◄─────┘
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL database (Supabase)
- Google Cloud project with Gmail API enabled

### 1. Clone
```bash
git clone https://github.com/SumitNagesia123/InboxToOffer.git
cd InboxToOffer
```

### 2. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # Fill in your DATABASE_URL and keys
uvicorn app.main:app --reload
```
API runs at `http://localhost:8000` (docs at `/docs`).

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at `http://localhost:5173`.

## Environment Variables

**Backend (`backend/.env`)**
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `SECRET_KEY` | Random secret string used to sign JWTs |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Allowed frontend URL(s) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |

**Frontend (`frontend/.env`)**
| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (e.g., `https://inboxtooffer.onrender.com/api/v1`) |

> Never commit `.env` files or real secrets.

## Deployment
- **Database:** Supabase (PostgreSQL managed DB with pre-configured schema tables).
- **Backend:** Render web service (Python runtime, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
- **Frontend:** Vercel static site deployment with SPA rewrites.
- **24/7 Keep-Alive:** UptimeRobot configured to ping `https://inboxtooffer.onrender.com/health` every 5 minutes.

## API Overview
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Log in |
| POST | `/api/v1/auth/quick-login` | Quick demo session login |
| GET | `/api/v1/jobs` | List extracted jobs |
| GET | `/api/v1/matches` | Resume-matched jobs |
| GET | `/api/v1/applications` | Application pipeline |

Full interactive docs: [API Docs](https://inboxtooffer.onrender.com/docs).

## Project Structure
```
InboxToOffer/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    REST endpoints (auth, jobs, matches, apps)
│   │   ├── core/                Config, security, encryption, logging
│   │   ├── database/            Session management & base model
│   │   ├── models/              SQLAlchemy ORM models
│   │   ├── schemas/             Pydantic request/response schemas
│   │   └── services/            Ingestion, triage, matching engine
│   ├── alembic/                 Database migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/                 API client
│       ├── components/          UI components
│       └── pages/               Dashboard, Matches, Applications, etc.
└── README.md
```

## Roadmap
- [x] Gmail OAuth & IMAP sync
- [x] AI triage & job extraction
- [x] Resume matching & explainability
- [x] Application pipeline tracking
- [x] Production deployment on Render & Vercel
- [ ] Outlook / Yahoo Mail support
- [ ] Browser extension for one-click apply tracking

## License
Distributed under the MIT License. See `LICENSE` for details.

## Contact
Sumit Nagesia · [LinkedIn](https://linkedin.com/in/sumit-nagesia) · sumitnagesia826@gmail.com
