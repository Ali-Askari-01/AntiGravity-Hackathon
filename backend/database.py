import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

db_url = os.environ.get("DATABASE_URL", "")

if db_url:
    if db_url.startswith("postgres"):
        engine = create_engine(db_url, pool_pre_ping=True)
    else:
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    db_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    os.makedirs(db_dir, exist_ok=True)
    db_file = os.path.join(db_dir, "antigravity.db")
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()