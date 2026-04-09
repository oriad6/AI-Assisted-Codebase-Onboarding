import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = None
SessionLocal = None
Base = declarative_base()


def init_db():
    """Initialize the database engine and session factory."""
    global engine, SessionLocal
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL in .env")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
