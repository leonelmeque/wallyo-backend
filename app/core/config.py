"""Application configuration and environment variables."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        self.supabase_url: str = self._get_required_env("SUPABASE_URL")
        self.supabase_service_role_key: str = self._get_required_env(
            "SUPABASE_SERVICE_ROLE_KEY"
        )
        # Anon key is optional - used for user-scoped operations with RLS
        self.supabase_anon_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
        self.bucket: str = os.getenv("SUPABASE_BACKUP_BUCKET", "user-backups")
        self.port: Optional[int] = self._get_optional_int("PORT")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: Optional[str] = os.getenv("LOG_FILE")

    def _get_required_env(self, key: str) -> str:
        """Get a required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_optional_int(self, key: str) -> Optional[int]:
        """Get an optional integer environment variable."""
        value = os.getenv(key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None


# Global settings instance
settings = Settings()

