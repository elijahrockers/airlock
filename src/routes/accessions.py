import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.audit import log_action
from src.auth import User, get_current_user, require_broker
from src.database import get_db
from src.models import AccessionMapping, Study
from src.schemas import (
    AccessionBulkRevealResponse,
    AccessionMappingResponse,
    AccessionRevealResponse,
)
from src.security import decrypt

router = APIRouter(prefix="/api/v1/studies/{study_id}/accessions", tags=["accessions"])


async def _get_study_or_404(db: AsyncSession, study_id: uuid.UUID) -> Study:
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.get("", response_model=list[AccessionMappingResponse])
async def list_accessions(
    study_id: uuid.UUID,
    dataset_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    await _get_study_or_404(db, study_id)

    query = (
        select(AccessionMapping)
        .where(AccessionMapping.study_id == study_id)
        .order_by(AccessionMapping.created_at)
    )
    if dataset_id:
        query = query.where(AccessionMapping.dataset_manifest_id == dataset_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/reveal-all", response_model=AccessionBulkRevealResponse)
async def reveal_all_accessions(
    study_id: uuid.UUID,
    dataset_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_broker),
):
    await _get_study_or_404(db, study_id)

    query = (
        select(AccessionMapping)
        .where(AccessionMapping.study_id == study_id)
        .options(joinedload(AccessionMapping.patient_mapping))
        .order_by(AccessionMapping.created_at)
    )
    if dataset_id:
        query = query.where(AccessionMapping.dataset_manifest_id == dataset_id)

    result = await db.execute(query)
    mappings = result.scalars().unique().all()

    accessions = [
        AccessionRevealResponse(
            id=m.id,
            patient_mapping_id=m.patient_mapping_id,
            study_id=m.study_id,
            dataset_manifest_id=m.dataset_manifest_id,
            accession_number=decrypt(m.accession_encrypted),
            subject_id=m.patient_mapping.subject_id,
        )
        for m in mappings
    ]

    await log_action(
        db,
        actor=user.username,
        action="reveal_all_accessions",
        resource_type="study",
        resource_id=str(study_id),
        detail={"count": len(accessions), "dataset_id": str(dataset_id) if dataset_id else None},
    )
    await db.commit()

    return AccessionBulkRevealResponse(
        study_id=study_id,
        count=len(accessions),
        accessions=accessions,
    )


@router.get("/{accession_id}/reveal", response_model=AccessionRevealResponse)
async def reveal_accession(
    study_id: uuid.UUID,
    accession_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_broker),
):
    await _get_study_or_404(db, study_id)

    result = await db.execute(
        select(AccessionMapping)
        .where(AccessionMapping.id == accession_id)
        .options(joinedload(AccessionMapping.patient_mapping))
    )
    mapping = result.scalars().first()

    if not mapping or mapping.study_id != study_id:
        raise HTTPException(
            status_code=404, detail="Accession mapping not found in this study"
        )

    decrypted = decrypt(mapping.accession_encrypted)

    await log_action(
        db,
        actor=user.username,
        action="reveal_accession",
        resource_type="accession_mapping",
        resource_id=str(mapping.id),
        detail={"study_id": str(study_id)},
    )
    await db.commit()

    return AccessionRevealResponse(
        id=mapping.id,
        patient_mapping_id=mapping.patient_mapping_id,
        study_id=mapping.study_id,
        dataset_manifest_id=mapping.dataset_manifest_id,
        accession_number=decrypted,
        subject_id=mapping.patient_mapping.subject_id,
    )
