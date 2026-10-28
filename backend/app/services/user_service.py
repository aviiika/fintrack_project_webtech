from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.all import UserCreate
from app.utils.security import hash_password, verify_password

def get_user(db: Session, uid: int): return db.get(User, uid)
def get_by_email(db: Session, email: str):
    return db.scalar(select(User).where(User.email == email))
def create_user(db: Session, payload: UserCreate):
    u = User(email=payload.email, full_name=payload.full_name,
             hashed_password=hash_password(payload.password))
    db.add(u); db.commit(); db.refresh(u)
    return u
def authenticate(db: Session, email: str, password: str):
    u = get_by_email(db, email)
    return u if u and verify_password(password, u.hashed_password) else None
