"""Tests for storage repository."""

import pytest
from unittest.mock import Mock, patch

from app.features.storage.repository import StorageRepository


class TestStorageRepository:
    """Test StorageRepository class."""

    def test_create_signed_upload_url_success(self) -> None:
        """Test successful creation of signed upload URL."""
        mock_storage = Mock()
        mock_storage.create_signed_upload_url.return_value = {
            "data": {"token": "test-token-123"},
            "error": None,
        }

        mock_bucket = Mock()
        mock_bucket.create_signed_upload_url = mock_storage.create_signed_upload_url

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch("app.features.storage.repository.supabase", mock_supabase):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.create_signed_upload_url("backups/user-id/file.db.enc")

            assert result["data"]["token"] == "test-token-123"
            mock_supabase.storage.from_.assert_called_once_with("test-bucket")
            mock_storage.create_signed_upload_url.assert_called_once_with(
                "backups/user-id/file.db.enc"
            )

    def test_create_signed_upload_url_error(self) -> None:
        """Test that Supabase errors are raised as exceptions."""
        mock_storage = Mock()
        mock_storage.create_signed_upload_url.return_value = {
            "data": None,
            "error": {"message": "Permission denied"},
        }

        mock_bucket = Mock()
        mock_bucket.create_signed_upload_url = mock_storage.create_signed_upload_url

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch("app.features.storage.repository.supabase", mock_supabase):
            repo = StorageRepository()
            with pytest.raises(Exception, match="Error creating upload token"):
                repo.create_signed_upload_url("backups/user-id/file.db.enc")

    def test_create_signed_download_url_success(self) -> None:
        """Test successful creation of signed download URL."""
        mock_storage = Mock()
        mock_storage.create_signed_url.return_value = {
            "data": {"signedUrl": "https://signed-url.example.com"},
            "error": None,
        }

        mock_bucket = Mock()
        mock_bucket.create_signed_url = mock_storage.create_signed_url

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch("app.features.storage.repository.supabase", mock_supabase):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.create_signed_download_url(
                "backups/user-id/latest.json", expires_in=900
            )

            assert result["data"]["signedUrl"] == "https://signed-url.example.com"
            mock_supabase.storage.from_.assert_called_once_with("test-bucket")
            mock_storage.create_signed_url.assert_called_once_with(
                path="backups/user-id/latest.json", expires_in=900
            )

    def test_create_signed_download_url_error(self) -> None:
        """Test that Supabase errors are raised as exceptions."""
        mock_storage = Mock()
        mock_storage.create_signed_url.return_value = {
            "data": None,
            "error": {"message": "Object not found"},
        }

        mock_bucket = Mock()
        mock_bucket.create_signed_url = mock_storage.create_signed_url

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch("app.features.storage.repository.supabase", mock_supabase):
            repo = StorageRepository()
            with pytest.raises(Exception, match="Error creating signed URL"):
                repo.create_signed_download_url(
                    "backups/user-id/latest.json", expires_in=900
                )

    def test_repository_uses_default_bucket(self) -> None:
        """Test that repository uses default bucket from settings."""
        mock_storage = Mock()
        mock_storage.create_signed_upload_url.return_value = {
            "data": {"token": "test-token"},
            "error": None,
        }

        mock_bucket = Mock()
        mock_bucket.create_signed_upload_url = mock_storage.create_signed_upload_url

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch("app.features.storage.repository.supabase", mock_supabase):
            with patch("app.features.storage.repository.settings") as mock_settings:
                mock_settings.bucket = "default-bucket"
                repo = StorageRepository()
                repo.create_signed_upload_url("backups/user-id/file.db.enc")

                mock_supabase.storage.from_.assert_called_once_with("default-bucket")

