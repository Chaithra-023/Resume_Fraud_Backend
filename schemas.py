"""
schemas.py — Pydantic models for request/response validation.
"""

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


# ── Auth ──────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Fraud Result ──────────────────────────────────────

class FraudResultOut(BaseModel):
    filename: str
    fraud_score: float
    fraud_status: str
    reasons: List[str]
    extracted_preview: str


class ResumeResultOut(BaseModel):
    id: int
    filename: str
    fraud_score: float
    fraud_status: str
    reasons: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
