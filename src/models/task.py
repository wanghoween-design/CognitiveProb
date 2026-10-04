from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    status = Column(String, default="pending")
    # 推理完整结果（JSON）：/ask 存 {"answer": ...}，/reason 存全部字段
    # 有了它，/tasks/{id} 才算真正的"历史记录"
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda : datetime.now(timezone.utc))