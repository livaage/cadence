from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://competition_user:competition_password@localhost:5432/competition_db")

# Pool sized small on purpose. Cloud Run's blue-green deploy briefly runs the
# old + new revision at the same time, so each pool's max footprint doubles
# during a rollout. db-f1-micro caps Postgres at ~25 max_connections; with
# the default SQLAlchemy pool (5 + 10 overflow = 15), two revisions exhaust
# the ceiling and the new one can't even open a connection to run its
# startup migration. 2 + 3 = max 5 per revision keeps blue-green safe.
# pool_pre_ping catches the stale-after-idle-scale-down case so a quiet
# instance doesn't return a dead connection to the first incoming request.
engine = create_engine(
    DATABASE_URL,
    pool_size=2,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 