# db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# FIXME: to .env
DATABASE_URL = 'sqlite:///data/bot.db'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
