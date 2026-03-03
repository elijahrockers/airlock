# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

Airlock is a dataset deidentification registry for research data brokers at Houston Methodist. It tracks IRB protocols, cryptographic hash keys, patient identity mappings (MRN→Subject ID), accession numbers, and dataset manifests — all with column-level encryption and audit logging. The broker uploads a CSV of patient/accession data, Airlock stores it encrypted, and the researcher gets exported keys for deidentification in external tools (XNAT).

PHI and patient privacy are primary concerns. All test/fixture data is synthetic.

## Commands

```bash
# Backend
pip install -e ".[dev]"                   # Install with dev dependencies
uvicorn src.main:app --reload             # Dev server at localhost:8000
pytest                                    # Run all tests (99 tests, in-memory SQLite)
pytest tests/test_patients.py -k reveal   # Run specific tests
ruff check src/ tests/                    # Lint
python fixtures/seed_dev_data.py          # Seed dev database (12 studies, all statuses)

# Frontend
cd frontend
npm install
npm run dev                               # Vite dev server at localhost:5173 (proxies /api → :8000)
npm run build                             # tsc + vite build
npx tsc --noEmit                          # Type check only

# Database
docker compose up -d                      # Start Postgres 16 + pgAdmin (port 5050)
alembic upgrade head                      # Run migrations
```

## Environment Variables

All use `AIRLOCK_` prefix (Pydantic Settings in `src/config.py`):
- `AIRLOCK_MASTER_KEY` — Root key for HKDF derivation (defaults to insecure dev value)
- `AIRLOCK_DATABASE_URL` — Defaults to local Postgres from docker-compose (`asyncpg`)
- `AIRLOCK_CORS_ORIGINS` — Defaults to `["http://localhost:5173"]`
- `AIRLOCK_DEBUG` — Enables SQLAlchemy query echo

## Architecture

**Backend:** FastAPI (async) + SQLAlchemy 2.0 async + PostgreSQL. Six route modules under `src/routes/` registered in `src/main.py`. Auth is a stub (`src/auth.py`) returning a hardcoded `dev_user`, designed for LDAP/Entra ID swap-in.

**Frontend:** React 18 + Vite 6 + TypeScript (strict) + Tailwind CSS v4. Four pages: StudyList, StudyDetail, NewStudy, KeyManagement. React Router v6 with all routes nested under `components/Layout.tsx` (Outlet-based shell). API client in `frontend/src/api/client.ts` with typed fetch wrapper.

### Role System

Two roles: `broker` and `researcher`. In dev, roles are simulated via header, not real auth:
- Frontend persists role to `localStorage("airlock-role")`, defaults to `broker`
- Every API request includes `X-User-Role` header; backend reads it in `src/auth.py`
- Frontend nav filters by role: "New Request" (researcher), "Key Management" (broker)
- Broker-only endpoints use `require_broker` dependency (403 if not broker)
- Study creation is researcher-only (enforced in route handler, not via dependency)
- Researchers can only see/edit their own studies (`requested_by == username`)

### Study Status Lifecycle

```
pending_researcher → [researcher uploads CSV] → pending_broker
    → [broker approves dataset] → active → completed
    → [broker rejects] → rejected
[broker archives from any status] → archived
```

Dataset approval (`POST .../datasets/{id}/approve`) auto-transitions study from `pending_broker` → `active` and fires `send_approval_email()` (currently a stub that only audit-logs).

### Security Model (`src/security.py`)

HKDF-SHA256 derives two subkeys from the master key:
- **Encryption subkey** (info=`b"airlock-encryption"`) → Fernet symmetric encryption for MRNs, accession numbers, and key material at rest
- **HMAC subkey** (info=`b"airlock-hmac"`) → HMAC-SHA256 for deterministic O(1) lookups without decryption

Global keys are versioned (yearly rotation). Each dataset manifest records which global key version was used. Project keys are per-study and auto-created with the study via `src/routes/_helpers.create_project_key_for_study()`.

### Data Model (`src/models.py` — 8 tables)

Study → ProjectHashKey (1:1), PatientMapping (1:N), DatasetManifest (1:N), AccessionMapping (1:N). GlobalHashKey is independent (versioned). AuditLog is append-only. ReidentificationRequest belongs to Study. AccessionMapping has a denormalized `study_id` FK for query convenience alongside `patient_mapping_id` and `dataset_manifest_id`.

Key constraints: `irb_pro_number` is unique across all studies. PatientMapping has unique constraints on both `(study_id, mrn_hash)` and `(study_id, subject_id)`. AccessionMapping has unique constraint on `(study_id, accession_hash)`.

### Dataset Upload Flow (`src/routes/datasets.py`)

`_process_dataset_upload()` is the shared core for both JSON and CSV endpoints. It:
1. Validates study not archived, active global key exists, researcher owns the study
2. Auto-advances study from `pending_researcher` → `pending_broker` on first upload
3. Checks MRN→subject_id consistency and accession uniqueness across all rows
4. Creates/reuses patient mappings via HMAC lookup (dedup)
5. Creates DatasetManifest + AccessionMapping records in one transaction

CSV endpoint (`upload-csv`) handles flexible column headers (case-insensitive, BOM-tolerant). CSV upload uses raw `fetch` (not the typed wrapper) because `Content-Type` must not be set for `FormData`.

### Route Ordering

Static paths like `reveal-all`, `lookup`, `date-offset`, `expiring` must be registered **before** parameterized paths like `{patient_id}/reveal` or `{study_id}` — otherwise FastAPI tries to parse the literal string as a UUID.

## Testing

Tests use in-memory SQLite (`aiosqlite`) with per-test transaction rollback for isolation. The `db_connection` fixture in `tests/conftest.py` wraps each test in a transaction; both `db` and `client` fixtures bind to the same connection so test data is visible to the HTTP client within the same transaction. No Postgres needed for tests.

Six test modules: `test_security`, `test_studies`, `test_datasets`, `test_patients`, `test_accessions`, `test_keys`.

## Conventions

- Python 3.10+, ruff (line-length=100, select E/F/I/W), pytest with asyncio_mode=auto
- TypeScript strict mode with `noUncheckedIndexedAccess` — array/object index access returns `T | undefined`
- Pydantic v2 schemas with `from_attributes=True` for ORM serialization
- All sensitive operations (key export, MRN/accession reveal, uploads) are audit-logged
- Migrations are hand-written Alembic (7 versions in `migrations/versions/`); `alembic.ini` has a hardcoded connection URL (does not read from env)
- `expire_on_commit=False` on async sessions — required so ORM attributes remain accessible after commit
- Queries using `joinedload` with `scalars()` require `.unique()` to deduplicate rows (see accession reveal endpoints)
- `requested_by` (set by backend to authenticated username) is distinct from `requestor` (freetext contact name field on Study)
