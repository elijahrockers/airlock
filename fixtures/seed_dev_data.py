"""Seed the dev database with sample data for manual testing."""

import asyncio

from src.database import async_session_factory, engine
from src.models import Base, DatasetManifest, DatasetType, GlobalHashKey, PatientMapping, Study
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
    },
    {
        "irb_pro_number": "PRO-2024-0107",
        "title": "Lung CT AI Training Dataset",
        "description": "Preparing deidentified lung CT scans for AI model training.",
        "pi_name": "Dr. Michael Park",
        "requestor": "Emily Rodriguez",
        "status": "active",
    },
    {
        "irb_pro_number": "PRO-2025-0003",
        "title": "Pathology Slide Anonymization",
        "description": "Deidentification of whole-slide pathology images.",
        "pi_name": "Dr. Lisa Patel",
        "status": "draft",
    },
]

PATIENTS = [
    ("MRN-100001", "SUBJ-A001"),
    ("MRN-100002", "SUBJ-A002"),
    ("MRN-100003", "SUBJ-A003"),
    ("MRN-200001", "SUBJ-B001"),
    ("MRN-200002", "SUBJ-B002"),
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

        # Add dataset manifests
        db.add(
            DatasetManifest(
                study_id=studies[0].id,
                global_hash_key_id=gk.id,
                global_key_version=gk.version,
                dataset_type=DatasetType.dicom_images,
                description="Cardiac MRI DICOM images — batch 1",
                record_count=450,
            )
        )
        db.add(
            DatasetManifest(
                study_id=studies[1].id,
                global_hash_key_id=gk.id,
                global_key_version=gk.version,
                dataset_type=DatasetType.dicom_images,
                description="Lung CT scans — training set",
                record_count=1200,
                metadata_json={"modality": "CT", "body_part": "chest"},
            )
        )

        await db.commit()
        print(f"Seeded {len(studies)} studies, {len(PATIENTS)} patients, 2 datasets, 1 global key")


if __name__ == "__main__":
    asyncio.run(seed())
