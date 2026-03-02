import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, get_current_user
from src.database import get_db
from src.models import Study, StudyStatus
from src.routes._helpers import create_project_key_for_study
from src.schemas import StudyCreate, StudyResponse, StudyUpdate

router = APIRouter(prefix="/api/v1/studies", tags=["studies"])


@router.get("", response_model=list[StudyResponse])
async def list_studies(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Study).order_by(Study.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=StudyResponse, status_code=201)
async def create_study(
    body: StudyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = Study(**body.model_dump())
    db.add(study)
    await db.flush()

    await create_project_key_for_study(db, study.id)

    await log_action(
        db,
        actor=user.username,
        action="create",
        resource_type="study",
        resource_id=str(study.id),
        detail={"irb_pro_number": study.irb_pro_number},
    )
    await db.commit()
    await db.refresh(study)
    return study


@router.get("/{study_id}", response_model=StudyResponse)
async def get_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.patch("/{study_id}", response_model=StudyResponse)
async def update_study(
    study_id: uuid.UUID,
    body: StudyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(study, field, value)

    await log_action(
        db,
        actor=user.username,
        action="update",
        resource_type="study",
        resource_id=str(study.id),
        detail={"fields": list(updates.keys())},
    )
    await db.commit()
    await db.refresh(study)
    return study


@router.delete("/{study_id}", status_code=204)
async def archive_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    study.status = StudyStatus.archived
    await log_action(
        db,
        actor=user.username,
        action="archive",
        resource_type="study",
        resource_id=str(study.id),
    )
    await db.commit()
