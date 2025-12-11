"""Tests for application configuration."""

import os
import pytest
from unittest.mock import patch

from app.core.config import Settings, settings


class TestSettings:
    """Test Settings class."""

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        },
        clear=True,
    )
    def test_settings_loads_required_env_vars(self) -> None:
        """Test that required environment variables are loaded."""
        test_settings = Settings()
        assert test_settings.supabase_url == "https://test.supabase.co"
        assert test_settings.supabase_service_role_key == "test-service-key"

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "BUCKET": "custom-bucket",
        },
        clear=True,
    )
    def test_settings_uses_custom_bucket(self) -> None:
        """Test that custom bucket name is loaded."""
        test_settings = Settings()
        assert test_settings.bucket == "custom-bucket"

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        },
        clear=True,
    )
    def test_settings_defaults_to_backups_bucket(self) -> None:
        """Test that bucket defaults to 'backups' if not set."""
        test_settings = Settings()
        assert test_settings.bucket == "backups"

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "PORT": "8787",
        },
        clear=True,
    )
    def test_settings_loads_port_as_int(self) -> None:
        """Test that PORT is loaded as integer."""
        test_settings = Settings()
        assert test_settings.port == 8787
        assert isinstance(test_settings.port, int)

    @patch.dict(
        os.environ,
        {"SUPABASE_URL": "https://test.supabase.co"},
        clear=True,
    )
    def test_settings_raises_on_missing_service_role_key(self) -> None:
        """Test that missing SUPABASE_SERVICE_ROLE_KEY raises ValueError."""
        with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
            Settings()

    @patch.dict(
        os.environ,
        {"SUPABASE_SERVICE_ROLE_KEY": "test-service-key"},
        clear=True,
    )
    def test_settings_raises_on_missing_supabase_url(self) -> None:
        """Test that missing SUPABASE_URL raises ValueError."""
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            Settings()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "PORT": "invalid",
        },
        clear=True,
    )
    def test_settings_handles_invalid_port_gracefully(self) -> None:
        """Test that invalid PORT value returns None."""
        test_settings = Settings()
        assert test_settings.port is None

