import os
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(data: dict) -> str:
    secret = os.getenv("JWT_SECRET", "change-this-secret")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    payload = data.copy()
    payload.update({"exp": expire})
    return jwt.encode(payload, secret, algorithm=algorithm)


def authenticate_with_database(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def authenticate_with_ldap(username: str, password: str) -> bool:
    # TODO SCRUM-1: connect to real Active Directory/LDAP.
    # Keep this adapter isolated so the login API does not change later.
    # Example future config:
    # LDAP_SERVER, LDAP_BASE_DN, LDAP_DOMAIN
    raise NotImplementedError("LDAP authentication is not implemented yet.")


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    provider = os.getenv("AUTH_PROVIDER", "database").lower()

    if provider == "database":
        return authenticate_with_database(db, username, password)

    if provider == "ldap":
        # First validate username/password against LDAP, then load/sync local profile.
        # For now, return None until LDAP is configured.
        return None

    raise RuntimeError(f"Unknown AUTH_PROVIDER: {provider}")
