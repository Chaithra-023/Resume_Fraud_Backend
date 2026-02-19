"""
fraud_checker.py — Advanced fraud scoring engine for resume text.

Scoring rules (0–100, capped):
  +25  Missing GitHub URL
  +25  Missing LinkedIn URL
  +30  GitHub username ≠ candidate name
  +30  LinkedIn username ≠ candidate name
  +30  Experience > (current_year − graduation_year)
  +20  Graduation year in the future
  +15  Any single word repeated > 25 times
  auto  Suspicious if experience > 40 years
  reject  If extracted text < 50 characters
"""

import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any

from utils import logger


# ── Regex patterns ────────────────────────────────────

GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_-]+)", re.IGNORECASE
)
LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9_-]+)", re.IGNORECASE
)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)?", re.IGNORECASE
)
NAME_PATTERN = re.compile(
    r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})", re.MULTILINE
)


def _extract_name(text: str) -> str:
    """Attempt to extract the candidate's name (first line heuristic)."""
    match = NAME_PATTERN.search(text)
    return match.group(1).strip() if match else ""


def _normalize(name: str) -> str:
    """Lower, strip, and remove non-alpha characters for fuzzy comparison."""
    return re.sub(r"[^a-z]", "", name.lower())


def _name_matches(candidate_name: str, profile_username: str) -> bool:
    """Check if any part of the candidate name appears in the profile username."""
    if not candidate_name or not profile_username:
        return False
    norm_username = _normalize(profile_username)
    parts = candidate_name.lower().split()
    return any(part in norm_username for part in parts if len(part) > 2)


def _extract_graduation_year(text: str) -> int | None:
    """Return the most likely graduation year from the resume text."""
    years = [int(y) for y in YEAR_PATTERN.findall(text)]
    # Filter to reasonable graduation range
    grad_candidates = [y for y in years if 1970 <= y <= 2099]
    return min(grad_candidates) if grad_candidates else None


def _extract_experience_years(text: str) -> int | None:
    """Return the first experience-years mention found."""
    match = EXPERIENCE_PATTERN.search(text)
    return int(match.group(1)) if match else None


# ── Main scoring function ────────────────────────────

def check_fraud(text: str, filename: str) -> Dict[str, Any]:
    """
    Analyse the extracted resume text and return a fraud report dict:
      filename, fraud_score, fraud_status, reasons, extracted_preview
    """
    logger.info("Running fraud checks on: %s", filename)
    reasons: List[str] = []
    fraud_score = 0
    current_year = datetime.now().year

    # ── F) Empty resume check ─────────────────────────
    if len(text.strip()) < 50:
        logger.warning("Resume text too short (<50 chars): %s", filename)
        return {
            "filename": filename,
            "fraud_score": 100,
            "fraud_status": "Suspicious",
            "reasons": ["Resume content is empty or too short (< 50 characters)"],
            "extracted_preview": text[:300],
        }

    # ── A) GitHub & LinkedIn presence ─────────────────
    github_match = GITHUB_PATTERN.search(text)
    linkedin_match = LINKEDIN_PATTERN.search(text)

    if not github_match:
        fraud_score += 25
        reasons.append("Missing GitHub profile URL")
        logger.debug("Missing GitHub URL in %s", filename)

    if not linkedin_match:
        fraud_score += 25
        reasons.append("Missing LinkedIn profile URL")
        logger.debug("Missing LinkedIn URL in %s", filename)

    # ── B) Profile-name validation ────────────────────
    candidate_name = _extract_name(text)

    if github_match and candidate_name:
        gh_user = github_match.group(1)
        if not _name_matches(candidate_name, gh_user):
            fraud_score += 30
            reasons.append(
                f"GitHub username '{gh_user}' does not match candidate name '{candidate_name}'"
            )
            logger.debug("GitHub name mismatch: %s vs %s", gh_user, candidate_name)

    if linkedin_match and candidate_name:
        li_user = linkedin_match.group(1)
        if not _name_matches(candidate_name, li_user):
            fraud_score += 30
            reasons.append(
                f"LinkedIn username '{li_user}' does not match candidate name '{candidate_name}'"
            )
            logger.debug("LinkedIn name mismatch: %s vs %s", li_user, candidate_name)

    # ── C) Education vs Experience ────────────────────
    grad_year = _extract_graduation_year(text)
    exp_years = _extract_experience_years(text)

    if grad_year and grad_year > current_year:
        fraud_score += 20
        reasons.append(f"Graduation year ({grad_year}) is in the future")
        logger.debug("Future graduation year: %d", grad_year)

    if grad_year and exp_years:
        max_possible = current_year - grad_year
        if max_possible >= 0 and exp_years > max_possible:
            fraud_score += 30
            reasons.append(
                f"Claimed {exp_years} years experience but graduated in {grad_year} "
                f"(max possible: {max_possible} years)"
            )
            logger.debug("Experience mismatch: claimed %d, max %d", exp_years, max_possible)

    # ── D) Repeated-word detection ────────────────────
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    word_counts = Counter(words)
    repeated = [w for w, c in word_counts.items() if c > 25]
    if repeated:
        fraud_score += 15
        reasons.append(f"Words repeated excessively (>25 times): {', '.join(repeated[:5])}")
        logger.debug("Repeated words detected: %s", repeated[:5])

    # ── E) Unrealistic experience ─────────────────────
    if exp_years and exp_years > 40:
        fraud_score = max(fraud_score, 50)  # ensure at least Suspicious
        reasons.append(f"Unrealistic experience claimed: {exp_years} years (>40)")
        logger.debug("Unrealistic experience: %d years", exp_years)

    # ── Cap and determine status ──────────────────────
    fraud_score = min(fraud_score, 100)
    fraud_status = "Suspicious" if fraud_score >= 50 else "Genuine"

    logger.info(
        "Fraud result for %s — score: %d, status: %s", filename, fraud_score, fraud_status
    )

    return {
        "filename": filename,
        "fraud_score": fraud_score,
        "fraud_status": fraud_status,
        "reasons": reasons,
        "extracted_preview": text[:300],
    }
