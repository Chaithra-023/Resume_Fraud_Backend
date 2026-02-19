"""
models.py — SQLAlchemy ORM models for User and ResumeResult tables.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    results = relationship("ResumeResult", back_populates="owner")


class ResumeResult(Base):
    __tablename__ = "resume_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    fraud_score = Column(Float, nullable=False)
    fraud_status = Column(String(50), nullable=False)
    reasons = Column(Text, nullable=True)          # stored as JSON string
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="results")
