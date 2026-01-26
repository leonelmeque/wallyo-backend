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


class TestStorageRepositoryListFiles:
    """Tests for list_user_files method."""

    def test_list_user_files_success(self) -> None:
        """Test successful listing of user files."""
        mock_bucket = Mock()
        mock_bucket.list.return_value = [
            {"name": "2025-01-25T10-00-00-aabbccdd.db.enc", "id": "1"},
            {"name": "2025-01-26T10-00-00-11223344.db.enc", "id": "2"},
            {"name": "latest.json", "id": "3"},
        ]

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch(
            "app.core.supabase.get_supabase_client", return_value=mock_supabase
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.list_user_files("user-123")

            assert len(result) == 3
            assert result[0]["name"] == "2025-01-25T10-00-00-aabbccdd.db.enc"
            mock_supabase.storage.from_.assert_called_with("test-bucket")
            mock_bucket.list.assert_called_once_with(path="user-123")

    def test_list_user_files_empty_directory(self) -> None:
        """Test listing when user has no files."""
        mock_bucket = Mock()
        mock_bucket.list.return_value = []

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch(
            "app.core.supabase.get_supabase_client", return_value=mock_supabase
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.list_user_files("user-123")

            assert result == []

    def test_list_user_files_with_user_token(self) -> None:
        """Test listing with user token for RLS."""
        mock_bucket = Mock()
        mock_bucket.list.return_value = [{"name": "file.db.enc"}]

        mock_user_client = Mock()
        mock_user_client.storage.from_.return_value = mock_bucket

        with patch.object(
            StorageRepository, "_get_user_client", return_value=mock_user_client
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.list_user_files("user-123", user_token="jwt-token")

            assert len(result) == 1
            mock_user_client.storage.from_.assert_called_with("test-bucket")


class TestStorageRepositoryDeleteFiles:
    """Tests for delete_files method."""

    def test_delete_files_success(self) -> None:
        """Test successful deletion of files."""
        mock_bucket = Mock()
        mock_bucket.remove.return_value = [
            {"name": "user-123/file1.db.enc"},
            {"name": "user-123/file2.db.enc"},
        ]

        mock_supabase = Mock()
        mock_supabase.storage.from_.return_value = mock_bucket

        with patch(
            "app.core.supabase.get_supabase_client", return_value=mock_supabase
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            paths = ["user-123/file1.db.enc", "user-123/file2.db.enc"]
            result = repo.delete_files(paths)

            assert len(result) == 2
            mock_bucket.remove.assert_called_once_with(paths)

    def test_delete_files_empty_list(self) -> None:
        """Test that empty list returns early without calling Supabase."""
        mock_supabase = Mock()

        with patch(
            "app.core.supabase.get_supabase_client", return_value=mock_supabase
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.delete_files([])

            assert result == []
            mock_supabase.storage.from_.assert_not_called()

    def test_delete_files_with_user_token(self) -> None:
        """Test deletion with user token for RLS."""
        mock_bucket = Mock()
        mock_bucket.remove.return_value = [{"name": "user-123/file.db.enc"}]

        mock_user_client = Mock()
        mock_user_client.storage.from_.return_value = mock_bucket

        with patch.object(
            StorageRepository, "_get_user_client", return_value=mock_user_client
        ):
            repo = StorageRepository(bucket_name="test-bucket")
            result = repo.delete_files(
                ["user-123/file.db.enc"], user_token="jwt-token"
            )

            assert len(result) == 1
            mock_user_client.storage.from_.assert_called_with("test-bucket")

