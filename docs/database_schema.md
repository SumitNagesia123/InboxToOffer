# Database Schema Specification — AI Job Email Intelligence System

This document outlines the relational database schema and vector embedding design for PostgreSQL with `pgvector`.

---

## 1. Extension Requirements

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

---

## 2. Table Schemas

### 2.1 `users`
Stores application user accounts.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
```

### 2.2 `oauth_credentials`
Stores encrypted Google OAuth tokens for Gmail access per user.

```sql
CREATE TABLE oauth_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) DEFAULT 'google' NOT NULL,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_uri VARCHAR(255) DEFAULT 'https://oauth2.googleapis.com/token' NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    scopes TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_oauth_user_id ON oauth_credentials(user_id);
```

### 2.3 `emails`
Metadata and raw text content of ingested Gmail messages.

```sql
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) NOT NULL,
    gmail_thread_id VARCHAR(255),
    sender VARCHAR(255) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    category VARCHAR(50) DEFAULT 'OTHER' NOT NULL, -- JOB, JOB_ALERT, APPLICATION_UPDATE, REJECTION, INTERVIEW, OFFER, OTHER
    classification_confidence FLOAT,
    classification_reason TEXT,
    processed_status VARCHAR(50) DEFAULT 'PENDING' NOT NULL, -- PENDING, PROCESSED, FAILED, SKIPPED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_gmail_msg UNIQUE (user_id, gmail_message_id)
);

CREATE INDEX idx_emails_user_id ON emails(user_id);
CREATE INDEX idx_emails_category ON emails(category);
CREATE INDEX idx_emails_status ON emails(processed_status);
```

### 2.4 `companies`
Normalized master records of companies extracted from jobs.

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255),
    logo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_companies_normalized_name ON companies(normalized_name);
```

### 2.5 `jobs`
Extracted structured job postings with vector embeddings for semantic deduplication and matching.

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_email_id UUID REFERENCES emails(id) ON DELETE SET NULL,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    company_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    normalized_title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    work_mode VARCHAR(50) DEFAULT 'UNKNOWN', -- REMOTE, HYBRID, ON_SITE, UNKNOWN
    employment_type VARCHAR(50) DEFAULT 'FULL_TIME', -- FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, UNKNOWN
    salary_currency VARCHAR(10),
    salary_min FLOAT,
    salary_max FLOAT,
    min_experience_years INT,
    max_experience_years INT,
    job_description TEXT,
    job_url TEXT,
    platform_source VARCHAR(100) DEFAULT 'OTHER', -- LinkedIn, Indeed, Naukri, Glassdoor, etc.
    posted_date TIMESTAMP WITH TIME ZONE,
    application_deadline TIMESTAMP WITH TIME ZONE,
    is_duplicate BOOLEAN DEFAULT FALSE NOT NULL,
    canonical_job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    embedding vector(384), -- 384-dimensional dense vector from sentence-transformers
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_title ON jobs(normalized_title);
CREATE INDEX idx_jobs_company ON jobs(company_name);
CREATE INDEX idx_jobs_embedding ON jobs USING hnsw (embedding vector_cosine_ops);
```

### 2.6 `skills`
Skill taxonomy master table.

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    normalized_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(100) -- Programming Languages, Frameworks, Databases, Cloud, Soft Skills, etc.
);

CREATE INDEX idx_skills_normalized ON skills(normalized_name);
```

### 2.7 `job_skills`
Junction table linking required and preferred skills to jobs.

```sql
CREATE TABLE job_skills (
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT TRUE NOT NULL,
    PRIMARY KEY (job_id, skill_id)
);
```

### 2.8 `resumes`
Candidate PDF resumes uploaded by users.

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    parsed_summary TEXT,
    total_experience_years FLOAT,
    education_summary JSONB,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
```

### 2.9 `resume_skills`
Junction table mapping extracted skills to user resumes.

```sql
CREATE TABLE resume_skills (
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    years_experience FLOAT,
    PRIMARY KEY (resume_id, skill_id)
);
```

### 2.10 `job_matches`
Explainable job-to-resume compatibility analysis.

```sql
CREATE TABLE job_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    overall_match_score FLOAT NOT NULL, -- 0.0 to 100.0
    skill_score FLOAT NOT NULL,
    experience_score FLOAT NOT NULL,
    semantic_score FLOAT NOT NULL,
    matched_skills JSONB NOT NULL,
    missing_required_skills JSONB NOT NULL,
    missing_preferred_skills JSONB NOT NULL,
    explanation_summary TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_job_match UNIQUE (user_id, job_id, resume_id)
);

CREATE INDEX idx_matches_user_id ON job_matches(user_id);
CREATE INDEX idx_matches_score ON job_matches(overall_match_score);
```

### 2.11 `applications`
Job application lifecycle status tracking per user.

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'DISCOVERED' NOT NULL, -- DISCOVERED, APPLIED, INTERVIEWING, REJECTED, OFFER, WITHDRAWN
    applied_date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_user_job_app UNIQUE (user_id, job_id)
);

CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(status);
```

### 2.12 `user_preferences` & `daily_digests`
User configuration and digest execution metrics.

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    digest_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    digest_time VARCHAR(10) DEFAULT '22:00' NOT NULL,
    preferred_work_modes JSONB,
    min_desired_salary FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    total_emails_processed INT NOT NULL,
    new_jobs_count INT NOT NULL,
    top_matches_count INT NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'SENT' NOT NULL
);
```

---

## 3. Data Integrity & Cascade Rules

- Delete Cascade: Deleting a `User` cascades to delete their `oauth_credentials`, `emails`, `jobs`, `resumes`, `job_matches`, `applications`, `user_preferences`, and `daily_digests`.
- Set Null: Deleting an `email` sets `jobs.source_email_id` to `NULL`, maintaining job history without breaking foreign key integrity.
