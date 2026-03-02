import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ProjectHashKey
from src.security import generate_key_material


async def create_project_key_for_study(db: AsyncSession, study_id: uuid.UUID) -> ProjectHashKey:
    """Generate and persist a project hash key for a new study."""
    key = ProjectHashKey(
        study_id=study_id,
        key_material=generate_key_material(),
    )
    db.add(key)
    await db.flush()
    return key
