import enum
from dataclasses import dataclass

from fastapi import HTTPException, Request


class UserRole(str, enum.Enum):
    broker = "broker"
    researcher = "researcher"


@dataclass
class User:
    username: str
    display_name: str
    role: UserRole = UserRole.broker


async def get_current_user(request: Request) -> User:
    """Auth stub — returns a hardcoded dev user.

    Replace with LDAP / Entra ID integration in production.
    Role is read from the X-User-Role header; defaults to broker.
    """
    role_header = request.headers.get("x-user-role", "broker")
    try:
        role = UserRole(role_header)
    except ValueError:
        role = UserRole.broker
    return User(username="dev_user", display_name="Development User", role=role)


async def require_broker(request: Request) -> User:
    """Dependency that enforces broker role. Raises 403 for researchers."""
    user = await get_current_user(request)
    if user.role != UserRole.broker:
        raise HTTPException(status_code=403, detail="Broker access required")
    return user
