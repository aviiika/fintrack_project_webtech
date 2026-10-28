from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.all import LoginRequest, Token, UserCreate, UserRead
from app.services import user_service
from app.utils.deps import CurrentUser, DbSession
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token, status_code=201)
async def register(payload: UserCreate, db: DbSession):
    if user_service.get_by_email(db, payload.email):
        raise HTTPException(409, "Email already registered")
    u = user_service.create_user(db, payload)
    return Token(access_token=create_access_token(u.id), user=UserRead.model_validate(u))

@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: DbSession):
    u = user_service.authenticate(db, payload.email, payload.password)
    if not u: raise HTTPException(401, "Incorrect email or password")
    return Token(access_token=create_access_token(u.id), user=UserRead.model_validate(u))

@router.post("/token", response_model=Token)
async def login_form(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    u = user_service.authenticate(db, form.username, form.password)
    if not u: raise HTTPException(401, "Incorrect email or password",
                                   headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(u.id), user=UserRead.model_validate(u))

@router.get("/me", response_model=UserRead)
async def me(cu: CurrentUser): return UserRead.model_validate(cu)
