from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gradescript.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_migrations():
    """Ensure database schema has all columns needed without requiring Alembic."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check if questions table exists
            res = conn.execute(text("PRAGMA table_info(questions);")).fetchall()
            col_names = [r[1] for r in res]
            if col_names and "question_type" not in col_names:
                conn.execute(text("ALTER TABLE questions ADD COLUMN question_type VARCHAR(50) DEFAULT 'subjective';"))
                conn.commit()
    except Exception as e:
        # Ignore if table doesn't exist yet or other DB engine
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
