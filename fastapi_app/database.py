# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Get environment config
ENVIRONMENT = os.getenv("ENVIRONMENT", "DEVELOPMENT").upper()
DATABASE_URL = os.getenv("DATABASE_URL")

# Resolve database URL based on environment
if ENVIRONMENT == "PRODUCTION":
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required in PRODUCTION mode.")
    # Standardize postgres:// to postgresql:// for SQLAlchemy compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if not DATABASE_URL.startswith("postgresql"):
        raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string in PRODUCTION mode.")
else:
    # Development mode default to SQLite if DATABASE_URL is not set
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./recommender.db"
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure connection args (needed for SQLite to allow multi-threaded access in FastAPI)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

