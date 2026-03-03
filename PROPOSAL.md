# HMH Research Data Deidentification Pipeline

## Purpose

Houston Methodist's research data pipeline implements the **honest broker model** per HIPAA §164.514(c), ensuring that no single actor or system holds both identified clinical data and the context to link it back to patients. The pipeline spans seven stages — from researcher request through final release to a compute cluster — across five systems: **Airlock** (governance registry), **XNAT/CTP** (deidentification engine for imaging data), **HPC** (staging and PHI screening), and **DGX/DHI** (AI/ML compute and consumption). Each stage enforces a separation of concerns so that deidentified data is never released without cryptographic key management, audit logging, and automated PHI screening.

## Why a Data Brokerage?

HIPAA's Privacy Rule permits the use of protected health information (PHI) for research, but only through controlled pathways. Under the Safe Harbor method (§164.514(b)), all 18 categories of identifiers must be removed before data qualifies as deidentified. The **honest broker** provision (§164.514(c)) designates a trusted intermediary — someone who is not a member of the research team — to perform or oversee this removal. Without a broker, researchers would need direct access to identified patient records, creating unnecessary exposure of PHI and placing the institution at compliance risk.

In practice, most institutions manage this process through spreadsheets, shared drives, and manual coordination between research teams, IT, and compliance. This is error-prone: crosswalk files are emailed or stored in plaintext, key material is reused or lost, and there is no auditable record of who accessed what, when, or under which IRB protocol. A single misplaced mapping file can constitute a reportable breach under the HITECH Act.

Airlock replaces this ad hoc process with a purpose-built registry. It encrypts all patient identifiers at rest, enforces per-study key isolation, logs every sensitive operation to an immutable audit trail, and provides the cryptographic keys that downstream deidentification tools need — without ever exposing identified data to the research team. The result is a repeatable, auditable pipeline that satisfies both the letter of HIPAA and the operational reality of a high-volume research institution.

## Pipeline Stages

### Stage 1 — Researcher Requests Data (Airlock)

**Who:** Researcher
**What:** The researcher creates a new study in Airlock under their IRB-approved protocol (PRO number), then uploads a CSV manifest of MRN, Subject ID, and Accession Number for the patients and imaging studies they need. Airlock encrypts all identifiers at rest (Fernet) and creates HMAC hashes for lookup without decryption. A per-study project key is auto-generated. The study enters the broker's review queue.

### Stage 2 — Broker Approves and Sets Deidentification Parameters (Airlock)

**Who:** Data Broker
**What:** The broker reviews the dataset manifest and either approves or rejects it. On approval, the broker sets a temporal policy for the study (date shifting, date removal, or no date handling) and exports the cryptographic keys (global hash key + project key) for use in the deidentification engine. Every key export is audit-logged. The study transitions to active status.

### Stage 3 — Data Deidentified Per IRB/Broker Parameters (XNAT/CTP)

**Who:** System (automated) / Broker
**What:** Using the exported keys, XNAT and its Clinical Trial Processor (CTP) pipeline perform DICOM PS3.15 tag-level deidentification — UID replacement, tag scrubbing (D/Z/X/K/C/U actions), date shifting using Airlock's per-patient HMAC-derived offset, and free-text field cleaning. Airlock does not perform deidentification; it provides the keys and crosswalk while XNAT is the deidentification engine.

### Stage 4 — Deidentified Data Stored in XNAT (XNAT)

**Who:** System (automated)
**What:** Deidentified DICOM data is stored in XNAT under a project corresponding to the Airlock study. Researchers access their deidentified datasets through XNAT's project-level permissions. The accession-level crosswalk in Airlock preserves the link between deidentified data and original studies for incidental finding workflows.

### Stage 5 — Data Staged on HPC (HPC)

**Who:** Broker / System
**What:** When deidentified data is ready for AI/ML workloads, it is transferred from XNAT to the HPC staging environment. This intermediate step provides a controlled handoff point before data enters the compute cluster, allowing for final review and automated PHI screening.

### Stage 6 — PHI Screening via dicom-phi-scan (HPC)

**Who:** System (automated)
**What:** Before release, all DICOM files on HPC pass through **dicom-phi-scan**, a two-layer PHI detection tool. Layer 1 checks ~40 DICOM header tags against HIPAA Safe Harbor identifiers, filtering known deidentification placeholders. Layer 2 runs OCR on pixel data to detect burned-in annotations — all detected text is conservatively flagged as PHI. This is a **gating step**: data that fails screening is held for broker review and remediation. Data that passes is cleared for release.

### Stage 7 — Release to DGX/DHI (DGX/DHI)

**Who:** System (automated) / Broker
**What:** Cleared data is pushed from HPC to the DGX cluster / Digital Health Institute environment, where it is available for AI and machine learning workloads. At this point, the data has passed through cryptographic deidentification, project-level isolation, and automated PHI screening.

## Flow

```
 Researcher        Broker            XNAT              HPC             DGX/DHI
 ──────────        ──────            ────              ───             ───────
     │                │                │                │                │
     │  1. Create     │                │                │                │
     │  study +       │                │                │                │
     │  upload CSV    │                │                │                │
     │ ── Airlock ──► │                │                │                │
     │                │                │                │                │
     │                │  2. Approve    │                │                │
     │                │  + temporal    │                │                │
     │                │    policy      │                │                │
     │                │  + export keys │                │                │
     │                │ ─── keys ────► │                │                │
     │                │                │                │                │
     │                │                │  3. Deidentify │                │
     │                │                │     (CTP tags, │                │
     │                │                │      UIDs,     │                │
     │                │                │      dates)    │                │
     │                │                │                │                │
     │                │                │  4. Store      │                │
     │                │                │     deidentified                │
     │                │                │     data       │                │
     │                │                │                │                │
     │                │                │ ── transfer ─► │                │
     │                │                │                │                │
     │                │                │                │  5. Stage data │
     │                │                │                │                │
     │                │                │                │  6. PHI screen │
     │                │                │                │  (dicom-phi-   │
     │                │                │                │   scan)        │
     │                │                │                │                │
     │                │                │            ┌───┤                │
     │                │                │            │   │                │
     │                │                │       PASS │   │ FAIL           │
     │                │                │            │   │   │            │
     │                │                │            │   │   ▼            │
     │                │                │            │   │ Remediate      │
     │                │◄───────────────│────────────│───┘   │            │
     │                │                │            │       │            │
     │                │                │            ▼       │            │
     │                │                │            │ ── push ────────► │
     │                │                │            │                   │
     │                │                │            │       7. Available│
     │                │                │            │       for AI/ML   │
     │                │                │            │       workloads   │
```

## Reidentification Path

When an incidental clinical finding occurs in deidentified data, HIPAA permits reidentification for patient safety. The honest broker workflow is:

1. Researcher reports the finding with the deidentified accession number
2. Broker uses Airlock's reveal endpoint to decrypt the original accession number (audit-logged)
3. Broker queries PACS by the original accession number to retrieve the clinical study
4. Clinical team is notified through standard institutional channels

Airlock's accession crosswalk and audit trail ensure this path is both possible and accountable. UID reversal is not needed — accession number lookup against PACS is sufficient for all reidentification scenarios.
