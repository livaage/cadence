import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import Teacher

# JWT_SECRET_KEY must be set in production. In dev we fall back to a per-process
# random key so tokens don't leak across restarts but the app still boots.
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(64)
ALGORITHM = "HS256"
# Long-ish TTL: teachers leave a notebook open all class. Trade-off favored
# convenience over short-lived token rotation; revisit if we add refresh tokens.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

async def get_current_teacher(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Teacher:
    """Get the current authenticated teacher"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        username = verify_token(credentials.credentials)
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    teacher = db.query(Teacher).filter(Teacher.username == username, Teacher.is_active == True).first()
    if teacher is None:
        raise credentials_exception

    return teacher


# A non-raising HTTPBearer so optional_teacher can return None when no header is sent.
_optional_security = HTTPBearer(auto_error=False)


async def optional_teacher(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
    db: Session = Depends(get_db),
) -> Optional[Teacher]:
    """Like get_current_teacher but returns None for unauthenticated requests.

    Lets endpoints accept either anonymous (token-only) callers or authenticated
    ones during the transition from teacher_token to teacher accounts."""
    if credentials is None:
        return None
    username = verify_token(credentials.credentials)
    if not username:
        return None
    return db.query(Teacher).filter(Teacher.username == username, Teacher.is_active == True).first()
