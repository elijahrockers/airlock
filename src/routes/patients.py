import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, get_current_user
from src.database import get_db
from src.models import PatientMapping, Study
from src.schemas import PatientLookupResponse, PatientMappingCreate, PatientMappingResponse
from src.security import decrypt, encrypt, hmac_hash

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
