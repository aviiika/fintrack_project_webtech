import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import settings

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(subject) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(subject), "exp": exp}, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict | None:
    try: return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError: return None
