
from fastapi import Cookie, Depends, HTTPException, status

from filestore.permissions import Actor

from .models import User
from .store import AuthStore
from .service import AuthService


SESSION_COOKIE_NAME = "session_token"


def get_auth_service() -> AuthService:
    return AuthService(AuthStore())


def require_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    service: AuthService = Depends(get_auth_service),
) -> User:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = service.get_current_user(session_token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return user


def require_actor(
    user: User = Depends(require_user),
) -> Actor:
    return Actor(
        user_id=user.id,
        role=user.role,
    )


def require_admin(
    actor: Actor = Depends(require_actor),
) -> Actor:
    if not actor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return actor
