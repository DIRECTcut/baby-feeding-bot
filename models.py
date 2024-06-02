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
    groups = relationship('Group', secondary='user_groups')

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    creator_id = Column(Integer, ForeignKey('users.id'))
    creator = relationship('User')
    members = relationship('User', secondary='user_groups')

class UserGroup(Base):
    __tablename__ = 'user_groups'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)

class FeedingLog(Base):
    __tablename__ = 'feeding_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    group_id = Column(Integer, ForeignKey('groups.id'))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship('User')
    group = relationship('Group')

# Create an engine and a session
# FIXME: to env
engine = create_engine('sqlite:///data/bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
