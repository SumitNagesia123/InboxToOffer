# AI Job Email Intelligence System — Architecture & System Design

## 1. Executive Summary & System Overview

The **AI Job Email Intelligence System** is a multi-tenant, privacy-focused platform that automatically connects to users' Gmail accounts via Google OAuth 2.0, ingests job-related emails, cleans and extracts structured job postings using NLP and LLM abstraction layers, detects duplicates across multiple job portals (LinkedIn, Indeed, Naukri, etc.), parses candidate resumes (PDF), computes explainable job-to-resume match scores, provides an interactive management dashboard, and automates daily job digest generation and email delivery.

---

## 2. High-Level System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND (SPA)                                       │
│                React 18 + TypeScript + Vite + Tailwind CSS + Recharts                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP / REST APIs (JWT Bearer Token)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND (FastAPI)                                    │
│                                                                                        │
│  ┌────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │   Auth & Middleware    │  │     API Controllers     │  │  Multi-Tenant Security  │  │
│  └───────────┬────────────┘  └────────────┬────────────┘  └────────────┬────────────┘  │
│              │                            │                            │               │
│              ▼                            ▼                            ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 SERVICE LAYER                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │  │
│  │  │ AuthService  │  │ GmailService │  │  EmailParser  │  │  ResumeParserEngine │  │  │
│  │  └──────────────┘  └──────────────┘  └───────────────┘  └─────────────────────┘  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │  │
│  │  │ DeduperEngine│  │ MatchingEngine│  │ DigestService │  │ SchedulerBackground │  │  │
│  │  └──────────────┘  └──────────────┘  └───────────────┘  └─────────────────────┘  │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │                                            │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                             AI & NLP ABSTRACTION LAYER                           │  │
│  │     ┌──────────────┐ ┌──────────────┐ ┌───────────────┐ ┌────────────────────┐     │  │
│  │     │ OllamaAdapter│ │ GeminiAdapter│ │ OpenAIAdapter │ │ AnthropicAdapter   │     │  │
│  │     └──────────────┘ └──────────────┘ └───────────────┘ └────────────────────┘     │  │
│  │     ┌───────────────────────────────┐ ┌──────────────────────────────────┐     │  │
│  │     │ spaCy / Text Cleaner          │ │ sentence-transformers (Embeddings) │     │  │
│  │     └───────────────────────────────┘ └──────────────────────────────────┘     │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ SQLAlchemy 2.0 ORM
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DATABASE (PostgreSQL)                                  │
│                   PostgreSQL 15+ with pgvector Extension Enabled                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Responsibilities

| Component Layer | Responsibility | Key Technologies |
| :--- | :--- | :--- |
| **Frontend UI** | Responsive SPA dashboard, login/register views, OAuth status, job filterable tables, match breakdown cards, resume uploader, application tracker, analytics charts, user settings. | React, TypeScript, Vite, Tailwind CSS, React Router, Recharts, React Hook Form, Zod, Axios |
| **API Layer** | Exposes REST endpoints, validates inputs via Pydantic schemas, handles CORS, JWT verification, exception handling, rate limiting. | FastAPI, Pydantic v2, Starlette |
| **Auth & Security** | User registration, password hashing (bcrypt), JWT access token generation, Fernet token encryption for OAuth secrets, row-level tenant authorization. | Passlib, PyJWT, Cryptography (Fernet) |
| **Gmail Integration** | Google OAuth 2.0 web flow, token refresh, Gmail API client, incremental email fetching, raw MIME parsing, HTML cleaning. | `google-api-python-client`, `google-auth-oauthlib`, `beautifulsoup4` |
| **NLP & AI Processing** | Email classification (JOB, REJECTION, OFFER, etc.), job detail extraction (salary, skills, work mode, etc.), resume text extraction & parsing. | PyMuPDF, spaCy, `sentence-transformers`, LLM Abstraction Layer (Gemini, Ollama, OpenAI, Anthropic) |
| **Deduplication Engine** | Identifies duplicate jobs across sources using exact URL matching, normalized company/title fingerprinting, and vector cosine similarity. | SQLAlchemy, `pgvector`, `scikit-learn` |
| **Matching Engine** | Compares job skill requirements, experience, work mode, and vector embeddings against user resume profile to generate explainable match breakdown scores. | Custom Python Matching Service + `pgvector` |
| **Daily Automation** | Periodic background jobs (10 PM daily processing), email ingestion, job extraction, deduplication, digest compilation, SMTP/Gmail email delivery. | APScheduler, Asyncio |
| **Database** | Persistent relational store for users, credentials, emails, extracted jobs, resumes, applications, analytics, and vector embeddings. | PostgreSQL, `pgvector`, SQLAlchemy 2.0, Alembic |

---

## 4. End-to-End Data Flow Pipeline

```text
1. Gmail Ingestion
   [Gmail API] ──► Fetch Raw Emails ──► MIME Parse & Clean HTML ──► Store Raw Metadata in `emails` table

2. Classification & Filtering
   Raw Email Content ──► NLP / LLM Classifier ──► Classify Category (JOB, REJECTION, OFFER, OTHER)
                                              └── Store classification confidence & explanation

3. Job Extraction
   JOB Email ──► LLM Extractor (Strict Pydantic JSON Schema) ──► Extract (Company, Title, Skills, Salary, WorkMode, URL)
                                                             └── Default missing fields to NULL/unknown

4. Deduplication & Vector Storage
   Extracted Job ──► Compute Vector Embedding ──► Check Existing Jobs (URL / Title+Company / Vector Cosine > 0.90)
                                              ├── IF Duplicate: Link `emails.job_id` to existing Job record
                                              └── IF New: Insert record into `jobs` and `job_skills` tables

5. Resume Processing & Match Engine
   Candidate PDF Resume ──► PyMuPDF Extract ──► LLM Resume Parser ──► Store `resumes` + `resume_skills` + Embedding
   Job Embedding + Resume Embedding + Skill Overlap ──► Match Engine ──► Generate Match Score & Breakdown ──► Store `job_matches`

6. Dashboard & Daily Automation
   Daily Scheduler (10 PM) ──► Execute Pipeline ──► Generate Markdown/HTML Digest ──► Deliver via Email ──► Update Analytics
```

---

## 5. Authentication & Security Architecture

### 5.1 Application Authentication
- **User Credentials**: Passwords are hashed with `bcrypt` (work factor 12) via `passlib`. Plaintext passwords are NEVER stored.
- **Session Tokens**: Stateless JSON Web Tokens (JWT) signed using `HS256` with configurable expiry (e.g., 60 minutes) and refresh tokens (7 days).
- **Authorization Middleware**: FastAPI dependency (`get_current_active_user`) injects the authenticated `User` object into endpoint handlers.

### 5.2 Gmail OAuth 2.0 Integration
- **OAuth Standard**: Google OAuth 2.0 Authorization Code Flow with PKCE.
- **Scopes Requested**: Least-privilege `https://www.googleapis.com/auth/gmail.readonly` and `https://www.googleapis.com/auth/userinfo.email`.
- **Token Security**: OAuth `access_token` and `refresh_token` are encrypted before storing in `oauth_credentials` using symmetric Fernet encryption (`cryptography` library) with an application secret key (`OAUTH_ENCRYPTION_KEY`).

### 5.3 Multi-Tenant Isolation
- **Row-Level User Binding**: Every table storing user data (`emails`, `jobs`, `resumes`, `job_matches`, `applications`, `user_preferences`) contains a non-nullable `user_id` foreign key referencing `users.id`.
- **Enforced Query Scoping**: Every database query in services explicitly filters by `filter(Model.user_id == current_user.id)`. Cross-user data access attempts return standard HTTP 404/403 errors.

---

## 6. Gmail Integration Architecture

1. **Connection Setup**: Frontend redirects user to `/api/v1/gmail/connect`, generating a Google OAuth consent URL stateful CSRF token.
2. **OAuth Callback**: `/api/v1/gmail/callback` exchanges authorization code for tokens, encrypts refresh token, and saves connection status in `oauth_credentials`.
3. **Synchronization Logic**:
   - `GmailSyncService` queries Gmail messages using search filter: `q="subject:(job OR career OR interview OR offer OR application OR hiring)"`.
   - Performs incremental fetch tracking `last_synced_at` or `history_id`.
   - MIME Parser strips HTML noise, signatures, and tracking pixels using BeautifulSoup4.
4. **Disconnect & Revocation**: Revokes Google OAuth token via Google revocation endpoint and deletes stored credentials.

---

## 7. AI & NLP Abstraction Layer Architecture

To prevent vendor lock-in, the system implements a unified `LLMProviderInterface` adapter pattern:

```python
class LLMProviderInterface(ABC):
    @abstractmethod
    async def classify_email(self, subject: str, body: str) -> EmailClassificationResult:
        pass

    @abstractmethod
    async def extract_job_details(self, subject: str, body: str) -> ExtractedJobSchema:
        pass

    @abstractmethod
    async def parse_resume(self, resume_text: str) -> ExtractedResumeSchema:
        pass
```

### Supported Provider Adapters:
1. **GeminiAdapter**: Google Gemini 1.5/2.0 Flash via `google-generativeai` SDK.
2. **OllamaAdapter**: Local Ollama instance (e.g. Llama 3, Mistral) via HTTP API.
3. **OpenAIAdapter**: OpenAI GPT-4o / GPT-4o-mini via `openai` SDK.
4. **AnthropicAdapter**: Anthropic Claude 3.5 Sonnet via `anthropic` SDK.

### Hallucination Protection Safeguards:
- Strict JSON schema enforcement using Pydantic output parsers.
- Prompt directives instructing the LLM: *"If a field (e.g., salary, location, job URL) is not explicitly stated in the email text, return null. DO NOT invent or infer missing information."*

---

## 8. Database Design (Entity-Relationship & Schema)

### Tables Summary:
1. `users`: App accounts (email, password_hash, created_at, settings).
2. `oauth_credentials`: Encrypted Google OAuth refresh tokens & connection state per user.
3. `emails`: Ingested email metadata, raw content, category classification, and processing status.
4. `companies`: Normalized company master records (name, domain, logo_url).
5. `jobs`: Extracted structured job records (title, company_id, location, work_mode, salary, url, platform_source, pgvector embedding).
6. `skills`: Skill taxonomy master table (name, category).
7. `job_skills`: Many-to-many relationship mapping required/preferred skills to jobs.
8. `resumes`: Uploaded resume metadata, extracted text, raw file path, vector embedding.
9. `resume_skills`: Many-to-many relationship mapping skills extracted from candidate resumes.
10. `job_matches`: Job-to-resume compatibility analysis, overall score (0–100%), skill breakdown JSON, match explanation.
11. `applications`: Job application lifecycle tracker (STATUS: DISCOVERED, APPLIED, INTERVIEWING, REJECTED, OFFER).
12. `user_preferences`: User specific job hunt criteria (target roles, preferred work mode, min salary, digest notification time).
13. `processing_runs`: Audit trail of sync/pipeline executions (started_at, ended_at, emails_processed, jobs_extracted, status).
14. `processing_errors`: Detailed failure log for email sync or NLP extraction errors.
15. `notifications`: System notifications for actionable items.
16. `daily_digests`: History of generated daily digests sent to users.

---

## 9. REST API Architecture & Endpoints

Base URL: `/api/v1`

### Endpoint Overview:

```text
POST   /api/v1/auth/register          - Register new user
POST   /api/v1/auth/login             - Authenticate user & get JWT token
GET    /api/v1/auth/me                - Current user profile details

GET    /api/v1/gmail/connect          - Initiate Google OAuth redirect
GET    /api/v1/gmail/callback         - OAuth callback handler
GET    /api/v1/gmail/status           - Check Gmail connection status
POST   /api/v1/gmail/sync             - Trigger manual Gmail sync
DELETE /api/v1/gmail/disconnect       - Disconnect Gmail OAuth account

GET    /api/v1/emails                 - List ingested emails with filtering
GET    /api/v1/emails/{id}            - Detailed view of specific email

GET    /api/v1/jobs                   - List extracted jobs with search & filters
GET    /api/v1/jobs/{id}              - Detailed job information

POST   /api/v1/resume/upload          - Upload PDF resume
GET    /api/v1/resume                 - Get current user's structured resume

GET    /api/v1/matches                - List job matches ranked by score
GET    /api/v1/matches/{id}           - Detailed match breakdown & skill gap analysis

GET    /api/v1/applications           - List job application pipeline statuses
POST   /api/v1/applications           - Track new job application
PATCH  /api/v1/applications/{id}      - Update application status

GET    /api/v1/analytics              - Overview statistics, match trends, status distribution
GET    /api/v1/settings               - Fetch user preferences & digest settings
PATCH  /api/v1/settings               - Update user settings
```

---

## 10. Frontend Architecture

### Component Hierarchy & Page Structure:
```text
frontend/src/
├── components/
│   ├── common/        (Button, Card, Modal, Input, Badge, Table, Spinner)
│   ├── layout/        (AppLayout, Header, Sidebar, Container)
│   ├── auth/          (LoginForm, RegisterForm, ProtectedRoute)
│   ├── gmail/         (GmailStatusCard, SyncProgressBanner)
│   ├── jobs/          (JobCard, JobList, JobFilterBar, JobDetailModal)
│   ├── matches/       (MatchScoreBadge, SkillGapView, MatchExplanationCard)
│   ├── resume/        (ResumeUploadZone, StructuredResumeViewer)
│   └── applications/  (KanbanBoard, ApplicationStatusBadge)
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── DashboardPage.tsx
│   ├── JobsPage.tsx
│   ├── JobDetailsPage.tsx
│   ├── MatchesPage.tsx
│   ├── EmailsPage.tsx
│   ├── ResumePage.tsx
│   ├── ApplicationsPage.tsx
│   ├── AnalyticsPage.tsx
│   └── SettingsPage.tsx
├── context/           (AuthContext, GmailContext)
├── services/          (apiClient, authService, gmailService, jobService, matchService)
└── types/             (api.ts, job.ts, user.ts, resume.ts)
```

---

## 11. Background Processing & Daily Automation Architecture

- **Scheduler Engine**: APScheduler running in async background mode alongside FastAPI app.
- **Cron Configuration**: Executes daily at 10:00 PM user time zone (configurable).
- **Execution Task Flow**:
  1. Iterate over all users with active `oauth_credentials`.
  2. Perform incremental Gmail email sync.
  3. Run NLP email classifier & job extractor pipeline.
  4. Run deduplication engine.
  5. Compute job-resume match scores for newly extracted jobs.
  6. Compile daily HTML digest featuring top matched jobs & application updates.
  7. Send digest via Gmail API / SMTP.
  8. Log metrics into `processing_runs` and `daily_digests` tables.

---

## 12. Security & Privacy Safeguards

1. **No Password Storage for External Services**: Pure OAuth 2.0 tokens for Gmail; no IMAP/SMTP passwords ever requested.
2. **Secret Separation**: `.env.example` contains placeholders. Actual secrets kept in `.env` (excluded from version control).
3. **CORS & Input Validation**: Strict CORS origins and Pydantic validation prevent XSS and SQL injection.
4. **Data Isolation Tests**: Automated tests verify User A cannot query User B data by manipulating IDs in requests.

---

## 13. System Verification Plan

- **Architecture Compliance**: Verify all services follow standard modular separation of concerns.
- **Database Schema**: Validate tables, foreign keys, indexes, and pgvector extension via Alembic migration scripts.
- **API Spec Verification**: Inspect generated OpenAPI specs at `/docs` to confirm route structures and response types.
