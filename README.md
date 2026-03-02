# Airlock

**Dataset Deidentification Registry for Research Data Brokerage**

Airlock is an internal tool for data brokers who manage the deidentification of medical research datasets. It serves as the single source of truth for tracking IRB protocols, managing cryptographic hash keys, mapping patient identities to study-specific subject IDs, and recording dataset manifests — all with column-level encryption and append-only audit logging.

## The Problem

When a research team requests deidentified data, a data broker must coordinate several pieces of information that today live in spreadsheets, emails, and institutional memory:

- Which IRB protocol covers this dataset?
- Which global hash key version was applied?
- What is the study-specific project key?
- Which MRNs map to which subject IDs?
- What data was included, and when?

Losing track of any of these creates reidentification risk, compliance gaps, or the inability to reproduce a deidentification run. Airlock centralizes all of it behind an auditable API.

## Two-Layer Hashing Scheme

Airlock enforces a two-layer key architecture designed so that compromising a single layer is insufficient for reidentification:

```
                  ┌─────────────────┐
                  │   Master Key    │  (AIRLOCK_MASTER_KEY env var)
                  │   (HKDF root)   │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     Encryption subkey            HMAC subkey
     (Fernet, AES-128)          (SHA-256 MAC)
              │                         │
    ┌─────────┴─────────┐              │
    ▼                   ▼              ▼
 Global Key       Project Key     MRN lookups
 (versioned,      (one per        without
  rotated         study)          decryption
  yearly)
```

- **Global key** — versioned and rotated approximately yearly. Old datasets retain their original version.
- **Project key** — unique per study, auto-generated on study creation.
- **MRN storage** — encrypted at rest (Fernet) with a parallel HMAC-SHA256 hash for O(1) lookups without decryption.

The `/api/v1/keys/study/{id}/export` endpoint returns both decrypted keys for downstream tools (e.g., XNAT), and every export is audit-logged.

## Data Model

| Table | Purpose |
|-------|---------|
| **Study** | IRB protocol tracking (PRO number, PI, status lifecycle) |
| **GlobalHashKey** | Versioned global keys with active/retired lifecycle |
| **ProjectHashKey** | One per study, auto-generated on creation |
| **PatientMapping** | MRN-to-Subject ID per study (encrypted MRN, HMAC for lookup) |
| **DatasetManifest** | What data was included, record counts, which key version was used |
| **AuditLog** | Append-only record of every sensitive operation |

## API

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/health` | GET | Readiness check |
| `/api/v1/studies` | GET, POST | List and create studies |
| `/api/v1/studies/{id}` | GET, PATCH, DELETE | Detail, update, archive |
| `/api/v1/keys/global` | GET | List all global key versions |
| `/api/v1/keys/global/rotate` | POST | Rotate global key (retires current) |
| `/api/v1/keys/study/{id}/export` | GET | Export decrypted keys for downstream (audited) |
| `/api/v1/studies/{id}/patients` | GET, POST | List and add patient mappings |
| `/api/v1/studies/{id}/patients/lookup` | GET | Lookup by MRN using HMAC hash |
| `/api/v1/studies/{id}/datasets` | GET, POST | List and create dataset manifests |

## Tech Stack

- **Backend:** Python 3.10+ / FastAPI (async) / Pydantic v2
- **Database:** PostgreSQL 16 (Docker for local dev)
- **ORM:** SQLAlchemy 2.0 async + Alembic migrations
- **Crypto:** cryptography (Fernet + HKDF + HMAC-SHA256)
- **Frontend:** React 18 / Vite / TypeScript / Tailwind CSS v4
- **Auth:** Stubbed dependency — designed for LDAP / Entra ID swap-in

## Quick Start

```bash
# Start Postgres
docker compose up -d postgres

# Install backend
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Seed sample data (optional)
python fixtures/seed_dev_data.py

# Start API server
uvicorn src.main:app --reload        # http://localhost:8000

# Start frontend
cd frontend && npm install && npm run dev   # http://localhost:5173

# Run tests (27 tests, no Postgres required — uses in-memory SQLite)
pytest
```

## Project Structure

```
airlock/
├── src/
│   ├── main.py              # FastAPI app, lifespan, CORS, router wiring
│   ├── config.py            # Pydantic Settings (AIRLOCK_ env prefix)
│   ├── database.py          # Async engine + session factory
│   ├── models.py            # SQLAlchemy ORM models (6 tables)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── security.py          # Fernet encryption, HMAC, HKDF key derivation
│   ├── audit.py             # Audit log helper
│   ├── auth.py              # Auth stub (future LDAP/Entra ID)
│   └── routes/              # health, studies, keys, patients, datasets
├── tests/                   # 27 async tests with per-test transaction isolation
├── migrations/              # Alembic (async) with initial schema
├── fixtures/                # Dev data seeder
├── frontend/                # React SPA (study list, detail, key management)
├── docker-compose.yml       # Postgres 16 + pgAdmin
└── pyproject.toml           # ruff, pytest, setuptools
```

## Roadmap

- LDAP / Entra ID authentication
- Role-based access control
- Bulk CSV import/export for patient mappings
- Audit log viewer in UI
- Integration with dicom-phi-scan pipeline
- XNAT webhook/callback integration
