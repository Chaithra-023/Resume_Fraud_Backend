"""
main.py — FastAPI application with authentication and resume fraud detection routes.
"""

import os
import json
import shutil
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import User, ResumeResult
from schemas import UserCreate, UserOut, Token, FraudResultOut, ResumeResultOut
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from extractor import extract_text
from fraud_checker import check_fraud
from utils import logger

# ── App setup ─────────────────────────────────────────

app = FastAPI(
    title="Resume Fraud Detection API",
    description="Upload resumes and detect potential fraud using an advanced scoring engine.",
    version="1.0.0",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# ── Startup event ─────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """Create database tables and ensure the uploads directory exists."""
    Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info("Application started — tables created, uploads dir ready")


# ── Auth routes ───────────────────────────────────────

@app.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    logger.info("Signup attempt for username: %s", user_data.username)

    # Check for duplicate username or email
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("User created: %s (id=%d)", new_user.username, new_user.id)
    return new_user


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate and return a JWT access token."""
    logger.info("Login attempt for username: %s", form_data.username)

    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login for username: %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("Token issued for user: %s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}


# ── Resume upload route ──────────────────────────────

@app.post("/upload-resume", response_model=FraudResultOut)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF/DOCX resume, extract text, run fraud detection, and store results."""
    logger.info(
        "Resume upload by user '%s': %s", current_user.username, file.filename
    )

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only PDF and DOCX are accepted.",
        )

    # Save file to uploads/
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("File saved: %s", filepath)
    except Exception as e:
        logger.error("Failed to save file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Extract text
    try:
        text = extract_text(filepath)
    except Exception as e:
        logger.error("Text extraction failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract text from resume",
        )

    # Run fraud detection
    result = check_fraud(text, file.filename)

    # Persist result
    db_result = ResumeResult(
        user_id=current_user.id,
        filename=file.filename,
        fraud_score=result["fraud_score"],
        fraud_status=result["fraud_status"],
        reasons=json.dumps(result["reasons"]),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    logger.info(
        "Result stored (id=%d): score=%s, status=%s",
        db_result.id,
        result["fraud_score"],
        result["fraud_status"],
    )

    return result


# ── Results history route ─────────────────────────────

@app.get("/results", response_model=list[ResumeResultOut])
def get_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all past fraud-check results for the authenticated user."""
    logger.info("Fetching results for user: %s", current_user.username)
    results = (
        db.query(ResumeResult)
        .filter(ResumeResult.user_id == current_user.id)
        .order_by(ResumeResult.uploaded_at.desc())
        .all()
    )
    return results
