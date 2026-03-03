import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, get_current_user
from src.database import get_db
from src.models import GlobalHashKey, ProjectHashKey, Study
from src.schemas import GlobalHashKeyResponse, KeyExportResponse
from src.security import decrypt_key_material, generate_key_material

router = APIRouter(prefix="/api/v1/keys", tags=["keys"])


@router.get("/global", response_model=list[GlobalHashKeyResponse])
async def list_global_keys(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GlobalHashKey).order_by(GlobalHashKey.version.desc())
    )
    return result.scalars().all()


@router.post("/global/rotate", response_model=GlobalHashKeyResponse, status_code=201)
async def rotate_global_key(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Retire current active key
    result = await db.execute(
        select(GlobalHashKey).where(GlobalHashKey.is_active.is_(True))
    )
    current = result.scalar_one_or_none()

    next_version = 1
    if current:
        current.is_active = False
        current.retired_at = datetime.now(timezone.utc)
        next_version = current.version + 1

    new_key = GlobalHashKey(
        version=next_version,
        key_material=generate_key_material(),
        is_active=True,
    )
    db.add(new_key)

    await log_action(
        db,
        actor=user.username,
        action="rotate",
        resource_type="global_hash_key",
        resource_id=str(new_key.id),
        detail={"version": next_version},
    )
    await db.commit()
    await db.refresh(new_key)
    return new_key


@router.get("/study/{study_id}/export", response_model=KeyExportResponse)
async def export_keys(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get study
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    # Get project key
    result = await db.execute(
        select(ProjectHashKey).where(ProjectHashKey.study_id == study_id)
    )
    project_key = result.scalar_one_or_none()
    if not project_key:
        raise HTTPException(status_code=404, detail="Project key not found for study")

    # Get active global key
    result = await db.execute(
        select(GlobalHashKey).where(GlobalHashKey.is_active.is_(True))
    )
    global_key = result.scalar_one_or_none()
    if not global_key:
        raise HTTPException(status_code=404, detail="No active global key found")

    await log_action(
        db,
        actor=user.username,
        action="export_keys",
        resource_type="study",
        resource_id=str(study_id),
        detail={"global_key_version": global_key.version},
    )
    await db.commit()

    return KeyExportResponse(
        study_id=study_id,
        global_key=decrypt_key_material(global_key.key_material),
        global_key_version=global_key.version,
        project_key=decrypt_key_material(project_key.key_material),
        temporal_policy=study.temporal_policy,
    )
