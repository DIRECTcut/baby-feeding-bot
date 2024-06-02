# create_tables.py

from sqlalchemy import create_engine
from models import Base

# FIXME: to .env
DATABASE_URL = 'sqlite:///data/bot.db'  # Replace with your actual database URL

engine = create_engine(DATABASE_URL)

# Create all tables
Base.metadata.create_all(engine)
