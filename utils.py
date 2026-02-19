"""
utils.py — Centralized logging configuration and helper utilities.
"""

import logging
import os

# ── Logging setup ─────────────────────────────────────

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("resume_fraud")
logger.setLevel(logging.DEBUG)

logger.info("Logging initialised — file: %s", LOG_FILE)
