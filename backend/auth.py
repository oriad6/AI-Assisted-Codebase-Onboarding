import hashlib
from sqlalchemy.orm import Session
from models import User


def hash_password(password: str) -> str:
    """SHA-256 hash — matches the original Streamlit app behavior."""
    return hashlib.sha256(password.encode()).hexdigest()


def login_user(db: Session, username: str, password: str):
    """Returns the User object if credentials match, else None."""
    pw_hash = hash_password(password)
    return db.query(User).filter_by(username=username, password_hash=pw_hash).first()


def register_user(db: Session, username: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    try:
        if db.query(User).filter_by(username=username).first():
            return False, "Username already exists"
        new_user = User(username=username, password_hash=hash_password(password))
        db.add(new_user)
        db.commit()
        return True, "Registration successful!"
    except Exception as e:
        db.rollback()
        return False, str(e)
