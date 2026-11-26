from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from hbentory.backoffice.db import Users
from hbentory.backoffice.security import decode_access_token
from hbentory.backoffice.seed import get_engine

engine = get_engine()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

def get_db() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def get_current_active_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise credentials_exception from e

    sub = payload.get('sub') if isinstance(payload, dict) else None

    if sub is None or isinstance(sub, bool):
        raise credentials_exception

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        raise credentials_exception from e

    user = db.scalar(
              select(Users)
              .options(joinedload(Users.role), joinedload(Users.branch))
              .where(Users.user_id == user_id)
    )
    if user is None or user.status != "active" or user.role is None:
        raise credentials_exception
    return user


def require_admin(current_user: Annotated[Users, Depends(get_current_active_user)]) -> Users:
        if current_user.role is None or current_user.role.name != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You are not sudo'
            )
        return current_user


def require_common_user(
       current_user: Annotated[Users, Depends(get_current_active_user)],
    ) -> Users:
        """Ensure the authenticated active user is a common user assigned to a branch."""
        if (
            current_user.role is None
        or current_user.role.name != "common"
            or current_user.branch_id is None
        ):
            raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
                detail="Branch operator privileges required",
            )
        return current_user
