import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, get_current_user
from src.database import get_db
from src.models import DatasetManifest, GlobalHashKey, Study
from src.schemas import DatasetManifestCreate, DatasetManifestResponse

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

    # Get active global key
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
