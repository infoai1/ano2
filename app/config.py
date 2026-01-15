"""Configuration and logging setup for Annotation Tool v2."""
import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import structlog

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
UPLOADS_DIR = DATA_DIR / 'uploads'
EXPORTS_DIR = DATA_DIR / 'exports'
BACKUPS_DIR = DATA_DIR / 'backups'

# =============================================================================
# APP CONFIG
# =============================================================================

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod-1234567890')
DATABASE_URI = f"sqlite:///{DATA_DIR / 'annotation.db'}"
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

# =============================================================================
# DIRECTORIES
# =============================================================================

def ensure_dirs():
    """Create required directories if they don't exist."""
    for dir_path in [DATA_DIR, LOG_DIR, UPLOADS_DIR, EXPORTS_DIR, BACKUPS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

# =============================================================================
# LOGGING
# =============================================================================

_logger = None

def setup_logging(debug: bool = False):
    """Configure structured logging with structlog."""
    global _logger

    ensure_dirs()

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        # Console: human readable
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Production: JSON for parsing
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # File handler for persistent logs
    log_file = LOG_DIR / 'app.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)

    # Add file handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    _logger = structlog.get_logger()
    return _logger

def get_logger():
    """Get the configured logger, initializing if needed."""
    global _logger
    if _logger is None:
        _logger = setup_logging(debug=DEBUG)
    return _logger

# =============================================================================
# UI THEME (from PRD)
# =============================================================================

THEME = {
    'primary': '#1e3a5f',      # Deep blue
    'secondary': '#c9a227',    # Gold accent
    'accent': '#2d6a4f',       # Islamic green
    'background': '#f8f5f0',   # Warm paper
    'text': '#2c2c2c',         # Soft black
    'border': '#d4c5b0',       # Aged paper edge
}
