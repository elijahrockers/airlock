import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.auth import User, UserRole, get_current_user, require_broker
from src.database import get_db
from src.models import ReidentificationRequest, Study, StudyStatus
from src.routes._helpers import create_project_key_for_study
from src.schemas import (
    ReidentificationRequestCreate,
    ReidentificationRequestResolve,
    ReidentificationRequestResponse,
    StudyCreate,
    StudyResponse,
    StudyUpdate,
)

router = APIRouter(prefix="/api/v1/studies", tags=["studies"])


@router.get("", response_model=list[StudyResponse])
async def list_studies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Study).order_by(Study.created_at.desc())
    if user.role == UserRole.researcher:
        query = query.where(Study.requested_by == user.username)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=StudyResponse, status_code=201)
async def create_study(
    body: StudyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.researcher:
        raise HTTPException(status_code=403, detail="Only researchers can create studies")

    data = body.model_dump()
    data["status"] = StudyStatus.pending_researcher
    data["requested_by"] = user.username
    study = Study(**data)
    db.add(study)
    await db.flush()

    await create_project_key_for_study(db, study.id)

    await log_action(
        db,
        actor=user.username,
        action="request",
        resource_type="study",
        resource_id=str(study.id),
        detail={"irb_pro_number": study.irb_pro_number},
    )
    await db.commit()
    await db.refresh(study)
    return study


@router.get("/expiring", response_model=list[StudyResponse])
async def list_expiring_studies(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    today = date.today()
    result = await db.execute(
        select(Study)
        .where(Study.expiration_alert_date <= today)
        .where(Study.status != StudyStatus.archived)
        .order_by(Study.expiration_alert_date.asc())
    )
    return result.scalars().all()


@router.post("/{study_id}/reject", response_model=StudyResponse)
async def reject_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_broker),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study.status not in (StudyStatus.pending_researcher, StudyStatus.pending_broker):
        raise HTTPException(status_code=409, detail="Study is not in a pending status")

    study.status = StudyStatus.rejected
    await log_action(
        db,
        actor=user.username,
        action="reject",
        resource_type="study",
        resource_id=str(study.id),
    )
    await db.commit()
    await db.refresh(study)
    return study


@router.post(
    "/{study_id}/reidentification-requests",
    response_model=ReidentificationRequestResponse,
    status_code=201,
)
async def create_reidentification_request(
    study_id: uuid.UUID,
    body: ReidentificationRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if user.role == UserRole.researcher and study.requested_by != user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    req = ReidentificationRequest(
        study_id=study_id,
        requested_by=user.username,
        message=body.message,
    )
    db.add(req)
    await log_action(
        db,
        actor=user.username,
        action="create_reidentification_request",
        resource_type="reidentification_request",
        resource_id=str(study_id),
        detail={"message": body.message[:200]},
    )
    await db.commit()
    await db.refresh(req)
    return req


@router.get(
    "/{study_id}/reidentification-requests",
    response_model=list[ReidentificationRequestResponse],
)
async def list_reidentification_requests(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if user.role == UserRole.researcher and study.requested_by != user.username:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(ReidentificationRequest)
        .where(ReidentificationRequest.study_id == study_id)
        .order_by(ReidentificationRequest.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/{study_id}/reidentification-requests/{request_id}/resolve",
    response_model=ReidentificationRequestResponse,
)
async def resolve_reidentification_request(
    study_id: uuid.UUID,
    request_id: uuid.UUID,
    body: ReidentificationRequestResolve,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_broker),
):
    req = await db.get(ReidentificationRequest, request_id)
    if not req or req.study_id != study_id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status.value != "pending":
        raise HTTPException(status_code=409, detail="Request already resolved")

    req.status = body.status
    req.resolved_at = datetime.now(timezone.utc)
    req.resolved_by = user.username
    await log_action(
        db,
        actor=user.username,
        action="resolve_reidentification_request",
        resource_type="reidentification_request",
        resource_id=str(request_id),
        detail={"status": body.status.value},
    )
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/{study_id}", response_model=StudyResponse)
async def get_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await db.get(Study, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if user.role == UserRole.researcher and study.requested_by != user.username:
        raise HTTPException(status_code=403, detail="Access denied")
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

    if user.role == UserRole.researcher:
        if study.requested_by != user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        if study.status != StudyStatus.pending_researcher:
            raise HTTPException(
                status_code=403, detail="Can only update studies in 'pending_researcher' status"
            )

    updates = body.model_dump(exclude_unset=True)
    if user.role == UserRole.researcher:
        updates.pop("status", None)
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
    user: User = Depends(require_broker),
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
