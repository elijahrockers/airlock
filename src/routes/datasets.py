import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, UserRole, get_current_user
from src.database import get_db
from src.models import (
    AccessionMapping,
    DatasetManifest,
    DatasetType,
    GlobalHashKey,
    PatientMapping,
    Study,
    StudyStatus,
)
from src.schemas import (
    DatasetManifestCreate,
    DatasetManifestResponse,
    DatasetUploadRequest,
    DatasetUploadResponse,
    DatasetUploadRow,
)
from src.security import encrypt, hmac_hash

router = APIRouter(prefix="/api/v1/studies/{study_id}/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetManifestResponse])
async def list_datasets(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    result = await db.execute(
        select(DatasetManifest)
        .where(DatasetManifest.study_id == study_id)
        .order_by(DatasetManifest.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=DatasetManifestResponse, status_code=201)
async def create_dataset(
    study_id: uuid.UUID,
    body: DatasetManifestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    result = await db.execute(
        select(GlobalHashKey).where(GlobalHashKey.is_active.is_(True))
    )
    global_key = result.scalar_one_or_none()
    if not global_key:
        raise HTTPException(
            status_code=400,
            detail="No active global key. Rotate a global key first.",
        )

    manifest = DatasetManifest(
        study_id=study_id,
        global_hash_key_id=global_key.id,
        global_key_version=global_key.version,
        **body.model_dump(),
    )
    db.add(manifest)

    await log_action(
        db,
        actor=user.username,
        action="create_dataset",
        resource_type="dataset_manifest",
        resource_id=str(manifest.id),
        detail={
            "study_id": str(study_id),
            "dataset_type": body.dataset_type.value,
            "global_key_version": global_key.version,
        },
    )
    await db.commit()
    await db.refresh(manifest)
    return manifest


async def _process_dataset_upload(
    study_id: uuid.UUID,
    body: DatasetUploadRequest,
    db: AsyncSession,
    user: User,
) -> DatasetUploadResponse:
    """Shared logic for JSON and CSV upload endpoints."""
    # Validate study
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study.status == StudyStatus.archived:
        raise HTTPException(status_code=400, detail="Cannot upload to an archived study")

    if user.role == UserRole.researcher:
        if study.requested_by != user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        if study.status != StudyStatus.requested:
            raise HTTPException(
                status_code=409, detail="Can only upload to studies in 'requested' status"
            )

    # Validate active global key
    result = await db.execute(
        select(GlobalHashKey).where(GlobalHashKey.is_active.is_(True))
    )
    global_key = result.scalar_one_or_none()
    if not global_key:
        raise HTTPException(status_code=400, detail="No active global key. Rotate first.")

    # Phase 1: Validate CSV consistency (collect all errors)
    mrn_to_subject: dict[str, str] = {}
    seen_accessions: set[str] = set()
    errors: list[str] = []

    for i, row in enumerate(body.records):
        if row.mrn in mrn_to_subject:
            if mrn_to_subject[row.mrn] != row.subject_id:
                errors.append(
                    f"Row {i + 1}: MRN mapped to '{row.subject_id}' "
                    f"but earlier row mapped it to '{mrn_to_subject[row.mrn]}'"
                )
        else:
            mrn_to_subject[row.mrn] = row.subject_id

        if row.accession_number in seen_accessions:
            errors.append(
                f"Row {i + 1}: duplicate accession '{row.accession_number}' in upload"
            )
        seen_accessions.add(row.accession_number)

    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    # Phase 2: Create/reuse patient mappings
    patients_created = 0
    patients_reused = 0
    patient_map: dict[str, uuid.UUID] = {}  # mrn -> patient_mapping.id

    for mrn, subject_id in mrn_to_subject.items():
        mrn_hashed = hmac_hash(mrn)

        result = await db.execute(
            select(PatientMapping).where(
                PatientMapping.study_id == study_id,
                PatientMapping.mrn_hash == mrn_hashed,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.subject_id != subject_id:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"MRN already mapped in this study with subject_id "
                        f"'{existing.subject_id}', but upload specifies '{subject_id}'"
                    ),
                )
            patient_map[mrn] = existing.id
            patients_reused += 1
        else:
            result = await db.execute(
                select(PatientMapping).where(
                    PatientMapping.study_id == study_id,
                    PatientMapping.subject_id == subject_id,
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Subject ID '{subject_id}' already used in this study "
                        f"by a different MRN"
                    ),
                )

            mapping = PatientMapping(
                study_id=study_id,
                mrn_encrypted=encrypt(mrn),
                mrn_hash=mrn_hashed,
                subject_id=subject_id,
            )
            db.add(mapping)
            await db.flush()
            patient_map[mrn] = mapping.id
            patients_created += 1

    # Phase 3: Create dataset manifest
    manifest = DatasetManifest(
        study_id=study_id,
        global_hash_key_id=global_key.id,
        global_key_version=global_key.version,
        dataset_type=body.dataset_type,
        description=body.description,
        record_count=len(body.records),
    )
    db.add(manifest)
    await db.flush()

    # Phase 4: Create accession mappings
    accessions_created = 0
    for row in body.records:
        acc_hash = hmac_hash(row.accession_number)

        result = await db.execute(
            select(AccessionMapping).where(
                AccessionMapping.study_id == study_id,
                AccessionMapping.accession_hash == acc_hash,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Accession '{row.accession_number}' already exists in this study",
            )

        acc = AccessionMapping(
            patient_mapping_id=patient_map[row.mrn],
            study_id=study_id,
            dataset_manifest_id=manifest.id,
            accession_encrypted=encrypt(row.accession_number),
            accession_hash=acc_hash,
        )
        db.add(acc)
        accessions_created += 1

    await log_action(
        db,
        actor=user.username,
        action="upload_dataset",
        resource_type="dataset_manifest",
        resource_id=str(manifest.id),
        detail={
            "study_id": str(study_id),
            "dataset_type": body.dataset_type.value,
            "patients_created": patients_created,
            "patients_reused": patients_reused,
            "accessions_created": accessions_created,
            "global_key_version": global_key.version,
        },
    )
    await db.commit()
    await db.refresh(manifest)

    return DatasetUploadResponse(
        manifest=DatasetManifestResponse.model_validate(manifest),
        patients_created=patients_created,
        patients_reused=patients_reused,
        accessions_created=accessions_created,
    )


@router.post("/upload", response_model=DatasetUploadResponse, status_code=201)
async def upload_dataset(
    study_id: uuid.UUID,
    body: DatasetUploadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _process_dataset_upload(study_id, body, db, user)


@router.post("/upload-csv", response_model=DatasetUploadResponse, status_code=201)
async def upload_dataset_csv(
    study_id: uuid.UUID,
    file: UploadFile = File(...),
    dataset_type: DatasetType = Form(DatasetType.dicom_images),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM from Excel
    reader = csv.DictReader(io.StringIO(text))

    records: list[DatasetUploadRow] = []
    for i, row in enumerate(reader):
        normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
        mrn = normalized.get("mrn")
        subject_id = normalized.get("subject_id") or normalized.get("subject id")
        accession = (
            normalized.get("accession_number")
            or normalized.get("accession number")
            or normalized.get("accession")
        )
        if not all([mrn, subject_id, accession]):
            raise HTTPException(
                status_code=422,
                detail=f"Row {i + 1}: missing required column (mrn, subject_id, accession_number)",
            )
        records.append(
            DatasetUploadRow(mrn=mrn, subject_id=subject_id, accession_number=accession)
        )

    if not records:
        raise HTTPException(status_code=422, detail="CSV file contains no data rows")

    body = DatasetUploadRequest(
        dataset_type=dataset_type, description=description, records=records
    )
    return await _process_dataset_upload(study_id, body, db, user)
