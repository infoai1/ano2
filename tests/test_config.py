"""Tests for config and logging setup."""
import pytest
import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Test configuration values."""

    def test_base_dir_exists(self):
        """Config should define BASE_DIR."""
        from app.config import BASE_DIR
        assert BASE_DIR is not None
        assert isinstance(BASE_DIR, Path)

    def test_data_dir_exists(self):
        """Config should define DATA_DIR."""
        from app.config import DATA_DIR
        assert DATA_DIR is not None
        assert isinstance(DATA_DIR, Path)

    def test_log_dir_exists(self):
        """Config should define LOG_DIR."""
        from app.config import LOG_DIR
        assert LOG_DIR is not None
        assert isinstance(LOG_DIR, Path)

    def test_secret_key_defined(self):
        """Config should define SECRET_KEY."""
        from app.config import SECRET_KEY
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) >= 16

    def test_database_uri_defined(self):
        """Config should define DATABASE_URI."""
        from app.config import DATABASE_URI
        assert DATABASE_URI is not None
        assert 'sqlite' in DATABASE_URI


class TestLogging:
    """Test logging setup."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a structlog logger."""
        from app.config import get_logger
        logger = get_logger()
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logger_can_log_info(self):
        """Logger should be able to log info messages."""
        from app.config import get_logger
        logger = get_logger()
        # Should not raise
        logger.info("test_message", key="value")

    def test_logger_can_log_error(self):
        """Logger should be able to log error messages."""
        from app.config import get_logger
        logger = get_logger()
        # Should not raise
        logger.error("test_error", error_code=500)


class TestDirectories:
    """Test that required directories are created."""

    def test_data_dir_created(self):
        """DATA_DIR should be created if it doesn't exist."""
        from app.config import DATA_DIR, ensure_dirs
        ensure_dirs()
        assert DATA_DIR.exists()

    def test_log_dir_created(self):
        """LOG_DIR should be created if it doesn't exist."""
        from app.config import LOG_DIR, ensure_dirs
        ensure_dirs()
        assert LOG_DIR.exists()

    def test_uploads_dir_created(self):
        """uploads directory should be created."""
        from app.config import DATA_DIR, ensure_dirs
        ensure_dirs()
        assert (DATA_DIR / 'uploads').exists()
