from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

# Normalize postgres:// → postgresql:// (Render sets the former; SQLAlchemy 2.x requires the latter)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

# Handle SQLite vs PostgreSQL engine arguments
_is_sqlite = _db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# PostgreSQL needs pool_pre_ping to heal stale connections and pool_recycle
# to avoid "server closed the connection unexpectedly" after idle periods.
engine = create_engine(
    _db_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=not _is_sqlite,
    pool_recycle=300 if not _is_sqlite else -1,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
