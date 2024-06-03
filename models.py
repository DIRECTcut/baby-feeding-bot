# models.py

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)

class FeedingLog(Base):
    __tablename__ = 'feeding_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    feeding_type = Column(String)  # New column for feeding type
    user = relationship('User')

# Create an engine and a session
# FIXME: to env
engine = create_engine('sqlite:///data/bot.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
