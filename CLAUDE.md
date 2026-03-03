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
pytest                                    # Run all tests (48 tests, in-memory SQLite)
pytest tests/test_patients.py -k reveal   # Run specific tests
ruff check src/ tests/                    # Lint
python fixtures/seed_dev_data.py          # Seed dev database

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
- `AIRLOCK_MASTER_KEY` — Root key for HKDF derivation (required)
- `AIRLOCK_DATABASE_URL` — Defaults to local Postgres from docker-compose
- `AIRLOCK_CORS_ORIGINS` — Defaults to `http://localhost:5173`

## Architecture

**Backend:** FastAPI (async) + SQLAlchemy 2.0 async + PostgreSQL. Six route modules under `src/routes/` registered in `src/main.py`. Auth is a stub (`src/auth.py`) returning a hardcoded dev user, designed for LDAP/Entra ID swap-in.

**Frontend:** React 18 + Vite 6 + TypeScript (strict) + Tailwind CSS v4. Three pages: StudyList, StudyDetail, KeyManagement. API client in `frontend/src/api/client.ts` with typed fetch wrapper.

### Security Model (`src/security.py`)

HKDF-SHA256 derives two subkeys from the master key:
- **Encryption subkey** (info=`b"airlock-encryption"`) → Fernet symmetric encryption for MRNs, accession numbers, and key material at rest
- **HMAC subkey** (info=`b"airlock-hmac"`) → HMAC-SHA256 for deterministic O(1) lookups without decryption

Global keys are versioned (yearly rotation). Each dataset manifest records which global key version was used. Project keys are per-study and auto-created with the study.

### Data Model (`src/models.py` — 7 tables)

Study → ProjectHashKey (1:1), PatientMapping (1:N), DatasetManifest (1:N), AccessionMapping (1:N). GlobalHashKey is independent (versioned). AuditLog is append-only. AccessionMapping has a denormalized `study_id` FK for query convenience alongside `patient_mapping_id` and `dataset_manifest_id`.

### Dataset Upload Flow (`src/routes/datasets.py`)

`_process_dataset_upload()` is the shared core for both JSON and CSV endpoints. It:
1. Validates study not archived, active global key exists
2. Checks MRN→subject_id consistency and accession uniqueness across all rows
3. Creates/reuses patient mappings via HMAC lookup (dedup)
4. Creates DatasetManifest + AccessionMapping records in one transaction

CSV endpoint (`upload-csv`) handles flexible column headers (case-insensitive, BOM-tolerant).

### Route Ordering

Static paths like `reveal-all` must be registered **before** parameterized paths like `{patient_id}/reveal` — otherwise FastAPI tries to parse "reveal-all" as a UUID.

## Testing

Tests use in-memory SQLite (`aiosqlite`) with per-test transaction rollback for isolation. The `db_connection` fixture in `tests/conftest.py` wraps each test in a transaction; both `db` and `client` fixtures bind to the same connection. No Postgres needed for tests.

## Conventions

- Python 3.10+, ruff (line-length=100, select E/F/I/W), pytest with asyncio_mode=auto
- TypeScript strict mode with `noUncheckedIndexedAccess`
- Pydantic v2 schemas with `from_attributes=True` for ORM serialization
- All sensitive operations (key export, MRN/accession reveal, uploads) are audit-logged
- Migrations are hand-written Alembic (see `migrations/versions/`)
