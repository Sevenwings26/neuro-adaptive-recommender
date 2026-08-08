# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default SQLite database path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recommender.db")

# Create engine (connect_args is needed for SQLite to allow multi-threaded access in FastAPI)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
