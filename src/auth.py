from dataclasses import dataclass


@dataclass
class User:
    username: str
    display_name: str


async def get_current_user() -> User:
    """Auth stub — returns a hardcoded dev user.

    Replace with LDAP / Entra ID integration in production.
    """
    return User(username="dev_user", display_name="Development User")
