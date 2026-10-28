from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.services import user_service
from app.utils.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
DbSession = Annotated[Session, Depends(get_db)]

def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                        headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(token)
    if not payload: raise exc
    user = user_service.get_user(db, int(payload["sub"]))
    if not user or not user.is_active: raise exc
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
