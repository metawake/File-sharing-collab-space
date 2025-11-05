from sqlmodel import SQLModel, create_engine
from .config import settings
import os


db_url = settings.database_url or settings.sqlite_url
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, echo=False, connect_args=connect_args, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    os.makedirs(settings.storage_dir, exist_ok=True)

