from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda : datetime.now(timezone.utc))