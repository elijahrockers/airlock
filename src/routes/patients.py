import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, get_current_user
from src.database import get_db
from src.models import PatientMapping, Study, TemporalPolicy
from src.schemas import (
    DateOffsetResponse,
    PatientBulkRevealResponse,
    PatientLookupResponse,
    PatientMappingCreate,
    PatientMappingResponse,
    PatientRevealResponse,
)
from src.security import compute_date_offset, decrypt, encrypt, hmac_hash

router = APIRouter(prefix="/api/v1/studies/{study_id}/patients", tags=["patients"])


async def _get_study_or_404(db: AsyncSession, study_id: uuid.UUID) -> Study:
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.get("", response_model=list[PatientMappingResponse])
async def list_patients(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    await _get_study_or_404(db, study_id)
    result = await db.execute(
        select(PatientMapping)
        .where(PatientMapping.study_id == study_id)
        .order_by(PatientMapping.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=PatientMappingResponse, status_code=201)
async def add_patient(
    study_id: uuid.UUID,
    body: PatientMappingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_study_or_404(db, study_id)

    mrn_hashed = hmac_hash(body.mrn)

    # Check for duplicate MRN in this study
    existing = await db.execute(
        select(PatientMapping).where(
            PatientMapping.study_id == study_id,
            PatientMapping.mrn_hash == mrn_hashed,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="MRN already mapped in this study")

    # Check for duplicate subject_id in this study
    existing = await db.execute(
        select(PatientMapping).where(
            PatientMapping.study_id == study_id,
            PatientMapping.subject_id == body.subject_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Subject ID already used in this study")

    mapping = PatientMapping(
        study_id=study_id,
        mrn_encrypted=encrypt(body.mrn),
        mrn_hash=mrn_hashed,
        subject_id=body.subject_id,
    )
    db.add(mapping)

    await log_action(
        db,
        actor=user.username,
        action="add_patient",
        resource_type="patient_mapping",
        resource_id=str(mapping.id),
        detail={"study_id": str(study_id), "subject_id": body.subject_id},
    )
    await db.commit()
    await db.refresh(mapping)
    return mapping


@router.get("/lookup", response_model=PatientLookupResponse)
async def lookup_patient(
    study_id: uuid.UUID,
    mrn: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_study_or_404(db, study_id)

    mrn_hashed = hmac_hash(mrn)
    result = await db.execute(
        select(PatientMapping).where(
            PatientMapping.study_id == study_id,
            PatientMapping.mrn_hash == mrn_hashed,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Patient not found in this study")

    decrypted_mrn = decrypt(mapping.mrn_encrypted)

    await log_action(
        db,
        actor=user.username,
        action="lookup_patient",
        resource_type="patient_mapping",
        resource_id=str(mapping.id),
        detail={"study_id": str(study_id)},
    )
    await db.commit()

    return PatientLookupResponse(
        id=mapping.id,
        study_id=mapping.study_id,
        mrn=decrypted_mrn,
        subject_id=mapping.subject_id,
    )


@router.get("/date-offset", response_model=DateOffsetResponse)
async def get_date_offset(
    study_id: uuid.UUID,
    mrn: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await _get_study_or_404(db, study_id)

    if study.temporal_policy != TemporalPolicy.shifted:
        raise HTTPException(
            status_code=409,
            detail="Study temporal policy is not 'shifted'; date offsets are not applicable",
        )

    mrn_hashed = hmac_hash(mrn)
    result = await db.execute(
        select(PatientMapping).where(
            PatientMapping.study_id == study_id,
            PatientMapping.mrn_hash == mrn_hashed,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Patient not found in this study")

    offset = compute_date_offset(str(study_id), mrn)

    await log_action(
        db,
        actor=user.username,
        action="date_offset_lookup",
        resource_type="patient_mapping",
        resource_id=str(mapping.id),
        detail={"study_id": str(study_id)},
    )
    await db.commit()

    return DateOffsetResponse(
        study_id=study_id,
        subject_id=mapping.subject_id,
        date_offset_days=offset,
    )


@router.get("/reveal-all", response_model=PatientBulkRevealResponse)
async def reveal_all_patients(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await _get_study_or_404(db, study_id)
    is_shifted = study.temporal_policy == TemporalPolicy.shifted

    result = await db.execute(
        select(PatientMapping)
        .where(PatientMapping.study_id == study_id)
        .order_by(PatientMapping.created_at)
    )
    mappings = result.scalars().all()

    patients = []
    for m in mappings:
        mrn = decrypt(m.mrn_encrypted)
        offset = compute_date_offset(str(study_id), mrn) if is_shifted else None
        patients.append(
            PatientRevealResponse(
                id=m.id,
                study_id=m.study_id,
                mrn=mrn,
                subject_id=m.subject_id,
                date_offset_days=offset,
            )
        )

    await log_action(
        db,
        actor=user.username,
        action="reveal_all_patients",
        resource_type="study",
        resource_id=str(study_id),
        detail={"count": len(patients)},
    )
    await db.commit()

    return PatientBulkRevealResponse(
        study_id=study_id,
        count=len(patients),
        patients=patients,
    )


@router.get("/{patient_id}/reveal", response_model=PatientRevealResponse)
async def reveal_patient(
    study_id: uuid.UUID,
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await _get_study_or_404(db, study_id)

    mapping = await db.get(PatientMapping, patient_id)
    if not mapping or mapping.study_id != study_id:
        raise HTTPException(status_code=404, detail="Patient mapping not found in this study")

    decrypted_mrn = decrypt(mapping.mrn_encrypted)
    offset = (
        compute_date_offset(str(study_id), decrypted_mrn)
        if study.temporal_policy == TemporalPolicy.shifted
        else None
    )

    await log_action(
        db,
        actor=user.username,
        action="reveal_patient",
        resource_type="patient_mapping",
        resource_id=str(mapping.id),
        detail={"study_id": str(study_id)},
    )
    await db.commit()

    return PatientRevealResponse(
        id=mapping.id,
        study_id=mapping.study_id,
        mrn=decrypted_mrn,
        subject_id=mapping.subject_id,
        date_offset_days=offset,
    )
