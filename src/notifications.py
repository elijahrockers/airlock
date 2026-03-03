import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.audit import log_action
from src.models import Study

logger = logging.getLogger(__name__)


async def send_approval_email(
    study: Study,
    recipient: str,
    db: AsyncSession,
) -> None:
    """Notify a researcher that their study request was approved.

    Currently logs to audit + console. Replace the print with SMTP
    or an external notification service in production.
    """
    logger.info(
        "Study %s (%s) approved — would email %s",
        study.id,
        study.title,
        recipient,
    )
    await log_action(
        db,
        actor="system",
        action="send_approval_email",
        resource_type="study",
        resource_id=str(study.id),
        detail={"recipient": recipient},
    )
