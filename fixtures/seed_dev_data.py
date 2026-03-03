"""Seed the dev database with sample data for manual testing."""

import asyncio

from src.database import async_session_factory, engine
from src.models import (
    AccessionMapping,
    Base,
    DatasetManifest,
    DatasetType,
    GlobalHashKey,
    PatientMapping,
    Study,
    TemporalPolicy,
)
from src.routes._helpers import create_project_key_for_study
from src.security import encrypt, generate_key_material, hmac_hash

STUDIES = [
    {
        "irb_pro_number": "PRO-2024-0042",
        "title": "Cardiac MRI Deidentification Pilot",
        "description": "Pilot study for deidentifying cardiac MRI datasets for research sharing.",
        "pi_name": "Dr. Sarah Chen",
        "requestor": "John Williams",
        "status": "active",
        "temporal_policy": TemporalPolicy.shifted,
    },
    {
        "irb_pro_number": "PRO-2024-0107",
        "title": "Lung CT AI Training Dataset",
        "description": "Preparing deidentified lung CT scans for AI model training.",
        "pi_name": "Dr. Michael Park",
        "requestor": "Emily Rodriguez",
        "status": "active",
        "temporal_policy": TemporalPolicy.removed,
    },
    {
        "irb_pro_number": "PRO-2025-0003",
        "title": "Pathology Slide Anonymization",
        "description": "Deidentification of whole-slide pathology images.",
        "pi_name": "Dr. Lisa Patel",
        "status": "draft",
        "temporal_policy": TemporalPolicy.unshifted,
    },
]

PATIENTS = [
    ("MRN-100001", "SUBJ-A001"),
    ("MRN-100002", "SUBJ-A002"),
    ("MRN-100003", "SUBJ-A003"),
    ("MRN-200001", "SUBJ-B001"),
    ("MRN-200002", "SUBJ-B002"),
]

# (mrn, accession_number) — linked to patients above
ACCESSIONS_STUDY_0 = [
    ("MRN-100001", "ACC-2024-00101"),
    ("MRN-100001", "ACC-2024-00102"),
    ("MRN-100001", "ACC-2024-00103"),
    ("MRN-100002", "ACC-2024-00201"),
    ("MRN-100002", "ACC-2024-00202"),
    ("MRN-100003", "ACC-2024-00301"),
]

ACCESSIONS_STUDY_1 = [
    ("MRN-200001", "ACC-2025-00401"),
    ("MRN-200001", "ACC-2025-00402"),
    ("MRN-200002", "ACC-2025-00501"),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Create global key v1
        gk = GlobalHashKey(version=1, key_material=generate_key_material(), is_active=True)
        db.add(gk)
        await db.flush()

        studies = []
        for s_data in STUDIES:
            study = Study(**s_data)
            db.add(study)
            await db.flush()
            await create_project_key_for_study(db, study.id)
            studies.append(study)

        # Add patient mappings to the first study
        for mrn, subject_id in PATIENTS[:3]:
            mapping = PatientMapping(
                study_id=studies[0].id,
                mrn_encrypted=encrypt(mrn),
                mrn_hash=hmac_hash(mrn),
                subject_id=subject_id,
            )
            db.add(mapping)

        # Add patient mappings to the second study
        for mrn, subject_id in PATIENTS[3:]:
            mapping = PatientMapping(
                study_id=studies[1].id,
                mrn_encrypted=encrypt(mrn),
                mrn_hash=hmac_hash(mrn),
                subject_id=subject_id,
            )
            db.add(mapping)

        # Build MRN→patient mapping lookup for accession creation
        patient_lookup: dict[str, dict] = {}
        for mrn, subject_id in PATIENTS[:3]:
            patient_lookup[mrn] = {"study_idx": 0, "mapping": None}
        for mrn, subject_id in PATIENTS[3:]:
            patient_lookup[mrn] = {"study_idx": 1, "mapping": None}

        # Re-query patient mappings so we have their IDs
        await db.flush()

        # Add dataset manifests
        manifest_0 = DatasetManifest(
            study_id=studies[0].id,
            global_hash_key_id=gk.id,
            global_key_version=gk.version,
            dataset_type=DatasetType.dicom_images,
            description="Cardiac MRI DICOM images — batch 1",
            record_count=len(ACCESSIONS_STUDY_0),
        )
        db.add(manifest_0)

        manifest_1 = DatasetManifest(
            study_id=studies[1].id,
            global_hash_key_id=gk.id,
            global_key_version=gk.version,
            dataset_type=DatasetType.dicom_images,
            description="Lung CT scans — training set",
            record_count=len(ACCESSIONS_STUDY_1),
            metadata_json={"modality": "CT", "body_part": "chest"},
        )
        db.add(manifest_1)
        await db.flush()

        # Build MRN hash → patient mapping ID lookup
        from sqlalchemy import select

        result = await db.execute(select(PatientMapping))
        all_patients = result.scalars().all()
        mrn_hash_to_patient = {}
        for p in all_patients:
            mrn_hash_to_patient[p.mrn_hash] = p

        # Create accession mappings for study 0
        acc_count = 0
        for mrn, accession in ACCESSIONS_STUDY_0:
            patient = mrn_hash_to_patient[hmac_hash(mrn)]
            db.add(
                AccessionMapping(
                    patient_mapping_id=patient.id,
                    study_id=studies[0].id,
                    dataset_manifest_id=manifest_0.id,
                    accession_encrypted=encrypt(accession),
                    accession_hash=hmac_hash(accession),
                )
            )
            acc_count += 1

        # Create accession mappings for study 1
        for mrn, accession in ACCESSIONS_STUDY_1:
            patient = mrn_hash_to_patient[hmac_hash(mrn)]
            db.add(
                AccessionMapping(
                    patient_mapping_id=patient.id,
                    study_id=studies[1].id,
                    dataset_manifest_id=manifest_1.id,
                    accession_encrypted=encrypt(accession),
                    accession_hash=hmac_hash(accession),
                )
            )
            acc_count += 1

        await db.commit()
        print(
            f"Seeded {len(studies)} studies, {len(PATIENTS)} patients, "
            f"2 datasets, {acc_count} accessions, 1 global key"
        )


if __name__ == "__main__":
    asyncio.run(seed())
