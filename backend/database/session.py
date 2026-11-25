from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from ..config import DB_PATH
from .models import Base

engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Lightweight migrations for databases created before case notes and accounts existed.
    columns = {c["name"] for c in inspect(engine).get_columns("investigations")}
    with engine.begin() as connection:
        if "notes" not in columns:
            connection.execute(text("ALTER TABLE investigations ADD COLUMN notes TEXT NOT NULL DEFAULT ''"))
        if "owner_id" not in columns:
            connection.execute(text("ALTER TABLE investigations ADD COLUMN owner_id INTEGER REFERENCES users(id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_investigations_owner_id ON investigations (owner_id)"))
