# Airlock — Architecture Review & Roadmap

## What Airlock Does

Airlock is a **dataset deidentification registry** — the honest broker's tracking system. When a researcher needs deidentified DICOM images for a study, the workflow is:

1. An IRB-approved study is created in Airlock with a PRO number
2. The researcher provides a CSV of `MRN, Subject ID, Accession Number` to the data broker
3. The broker uploads the CSV to Airlock, which stores everything encrypted (Fernet) and creates HMAC hashes for O(1) lookups without decryption
4. Airlock generates two cryptographic keys per study: a **global hash key** (versioned, rotated yearly) and a **project key** (per-study)
5. The broker exports the keys and gives them to the researcher, who uses them in **XNAT** to actually perform the DICOM deidentification (UID replacement, tag scrubbing, etc.)
6. Every reveal, export, and upload is audit-logged

Critically, **Airlock does not perform deidentification itself**. It is the crosswalk manager and key vault — it tracks *who maps to whom* and *which keys were used*, while XNAT or CTP does the actual tag/pixel manipulation.

## Comparison to DICOM Deidentification Best Practices

### Where Airlock aligns well

| Practice | Airlock's Approach |
|---|---|
| **Honest broker separation** | Airlock is the broker's tool; researchers never access it. The crosswalk (MRN→Subject ID, Accession→hash) is encrypted at rest and only revealable by the broker. This matches HIPAA §164.514(c). |
| **Crosswalk security** | Column-level Fernet encryption for MRNs and accession numbers, HMAC-SHA256 for lookups without decryption, append-only audit log on every reveal/export. Separation of the crosswalk from the deidentified data. |
| **Consistent identifier remapping** | Patient dedup via HMAC ensures the same MRN always maps to the same Subject ID within a study. Accession mappings are unique-constrained per study. |
| **Key management** | Versioned global keys with rotation support. Dataset manifests record which key version was used, so old datasets remain interpretable. Per-study project keys provide isolation between studies. |
| **Audit trail** | Every sensitive operation (key export, MRN reveal, accession reveal, dataset upload) creates an immutable AuditLog record with actor, action, timestamp, and detail. |
| **Accession number tracking** | Accession numbers are treated as identifiers (HIPAA category #10/#18) and stored encrypted, not in plaintext — matching PS3.15 action code "Z" for tag (0008,0050). |

### What Airlock delegates (by design)

These are handled by downstream tools (XNAT, CTP) using the exported keys:

- **DICOM PS3.15 tag-level deidentification** — the hundreds of tag actions (D/Z/X/K/C/U) from Table E.1-1
- **UID replacement** — Study/Series/SOP Instance UIDs and cross-reference updates
- **Pixel PHI / burned-in annotation cleaning** — OCR detection and redaction
- **Private tag handling** — vendor-specific safe-list curation
- **Free-text field scrubbing** — Study Description, Protocol Name, etc.
- **Date shifting** — Airlock computes the per-patient offset; XNAT applies it to DICOM tags

This is a reasonable architectural boundary. Airlock is the *registry and key vault*; XNAT is the *deidentification engine*.

## Roadmap — Gaps to Address

### 1. ~~Date-shift offset tracking~~ ✅ Resolved

Implemented. Studies have a `temporal_policy` (enum: `none`, `shifted`, `removed`) and a per-patient date offset endpoint (`GET /api/v1/studies/{study_id}/patients/date-offset?mrn={mrn}`). When `temporal_policy=shifted`, a deterministic HMAC-based offset (±180 days) is computed per patient and returned to the broker for use in XNAT. The offset is derived from the project key + MRN, so it's consistent across requests without storing additional state. Key export includes the temporal policy so downstream tools know which date handling to apply.

### 2. ~~UID crosswalk~~ ✅ Resolved — not needed

After reviewing DICOM PS3.15 UID handling requirements, we determined a UID crosswalk is outside Airlock's scope:

- **PS3.15 Basic Profile requires UID replacement** (action "U") — XNAT generates new UIDs as a one-way operation during deidentification. This is a deidentification engine concern, not a registry concern.
- **Re-identification uses accession number → PACS, not UID reversal.** The honest broker workflow for incidental findings is: reveal accession number in Airlock → query PACS by accession → retrieve original study. UIDs are not needed for this path.
- **Airlock's accession crosswalk is sufficient** for all honest broker scenarios: incidental findings, longitudinal linking, and dataset provenance.
- **UID crosswalks belong to the deidentification engine** (e.g., CTP's IDMap). XNAT/CTP maintain their own UID mappings internally for cross-reference consistency during deidentification.

### 3. Pixel PHI status tracking

The sibling `dicom-phi-agent` project detects burned-in annotations, but Airlock doesn't record whether pixel screening was performed or what was found. A `pixel_screening_status` on DatasetManifest could close this loop.

### 4. PS3.15 profile declaration

Airlock doesn't record which deidentification profile/options were applied. Adding a `deid_profile` field to DatasetManifest (e.g., "Basic + Clean Pixel Data + Retain Longitudinal") would document compliance posture.

### 5. Re-identification workflow

HIPAA allows re-identification for clinical reasons (incidental findings). Airlock has the reveal endpoints, but there's no formalized re-identification request workflow with IRB approval tracking.

### 6. Key destruction policy

Best practice is to define retention schedules for crosswalk data aligned with the IRB protocol. Airlock has study lifecycle states (draft→active→completed→archived) but no key/crosswalk destruction mechanism.

## Summary

Airlock handles the **governance layer** — identity crosswalk, key management, audit trail — which is the part most institutions cobble together with spreadsheets, REDCap projects, or ad-hoc databases. It correctly separates this from the **deidentification engine** (XNAT/CTP). The security model (HKDF-derived subkeys, Fernet encryption, HMAC lookups, audit logging) is solid for the crosswalk use case. With date-offset tracking now implemented and the UID crosswalk question resolved, the remaining gaps are around tracking what the downstream deidentification engine *actually did* (which PS3.15 profile, pixel screening results) — metadata that would make Airlock a complete deidentification governance record rather than just a key vault.
