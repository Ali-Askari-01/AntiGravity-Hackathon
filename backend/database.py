import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

db_path = os.environ.get("DATABASE_URL", "")
if db_path:
    engine = create_engine(db_path, connect_args={"check_same_thread": False} if db_path.startswith("sqlite") else {})
else:
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_parent = os.path.dirname(db_dir)
    db_file = os.path.join(db_parent, "antigravity.db")
    db_path = f"sqlite:///{db_file}"
    engine = create_engine(db_path, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()