"""Tests for storage service."""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.features.storage.service import StorageService
from app.features.storage.repository import StorageRepository
from app.features.storage.schemas import PresignUploadRes, PresignDownloadRes


class TestStorageService:
    """Test StorageService class."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create a mock repository."""
        return Mock(spec=StorageRepository)

    @pytest.fixture
    def service(self, mock_repository: Mock) -> StorageService:
        """Create a service instance with mock repository."""
        return StorageService(mock_repository)

    def test_build_backup_paths_with_db_enc(self, service: StorageService) -> None:
        """Test path building for .db.enc files."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        data_path, latest_path = service.build_backup_paths(user_id, "wallyo.db.enc")

        assert data_path.startswith(f"backups/{user_id}/")
        assert data_path.endswith(".db.enc")
        assert "-" in data_path  # Should contain timestamp and random hex
        assert latest_path == f"backups/{user_id}/latest.json"

    def test_build_backup_paths_with_other_extension(
        self, service: StorageService
    ) -> None:
        """Test path building for other file types."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        data_path, latest_path = service.build_backup_paths(user_id, "backup.tar.gz")

        assert data_path.startswith(f"backups/{user_id}/")
        assert "backup.tar.gz" in data_path
        assert latest_path == f"backups/{user_id}/latest.json"

    def test_build_backup_paths_sanitizes_slashes(
        self, service: StorageService
    ) -> None:
        """Test that slashes in filename are replaced."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        data_path, _ = service.build_backup_paths(user_id, "path/to/file.db.enc")

        assert "/" not in data_path.split(f"backups/{user_id}/")[1]
        assert "_" in data_path  # Slashes should be replaced

    def test_validate_download_path_valid(self, service: StorageService) -> None:
        """Test that valid path passes validation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        path = f"backups/{user_id}/latest.json"

        # Should not raise
        service.validate_download_path(path, user_id)

    def test_validate_download_path_invalid_user(
        self, service: StorageService
    ) -> None:
        """Test that path for different user raises 403."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        other_user_id = "987fcdeb-51a2-43d7-b890-123456789abc"
        path = f"backups/{other_user_id}/latest.json"

        with pytest.raises(HTTPException) as exc_info:
            service.validate_download_path(path, user_id)

        assert exc_info.value.status_code == 403

    def test_validate_download_path_outside_backups(
        self, service: StorageService
    ) -> None:
        """Test that path outside backups/ raises 403."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        path = "other-bucket/user-id/file.json"

        with pytest.raises(HTTPException) as exc_info:
            service.validate_download_path(path, user_id)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_presign_upload_success(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test successful presign upload."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        filename = "wallyo.db.enc"

        mock_repository.create_signed_upload_url.side_effect = [
            {"data": {"token": "token1"}},
            {"data": {"token": "token2"}},
        ]

        result = await service.presign_upload(user_id, filename)

        assert isinstance(result, PresignUploadRes)
        assert result.path.startswith(f"backups/{user_id}/")
        assert result.token == "token1"
        assert result.latest_path == f"backups/{user_id}/latest.json"
        assert result.latest_token == "token2"
        assert mock_repository.create_signed_upload_url.call_count == 2

    @pytest.mark.asyncio
    async def test_presign_upload_with_slashes_in_filename(
        self, service: StorageService
    ) -> None:
        """Test that filename with slashes raises 400."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        with pytest.raises(HTTPException) as exc_info:
            await service.presign_upload(user_id, "path/to/file.db.enc")

        assert exc_info.value.status_code == 400
        assert "slashes" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_presign_upload_repository_error(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that repository errors are handled."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_repository.create_signed_upload_url.side_effect = Exception(
            "Supabase error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.presign_upload(user_id, "wallyo.db.enc")

        assert exc_info.value.status_code == 500
        assert "Failed to create upload tokens" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_presign_download_success(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test successful presign download."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        path = f"backups/{user_id}/latest.json"

        mock_repository.create_signed_download_url.return_value = {
            "data": {"signedUrl": "https://signed-url.example.com"}
        }

        result = await service.presign_download(user_id, path, 900)

        assert isinstance(result, PresignDownloadRes)
        assert result.url == "https://signed-url.example.com"
        mock_repository.create_signed_download_url.assert_called_once_with(
            path, 900
        )

    @pytest.mark.asyncio
    async def test_presign_download_invalid_path(
        self, service: StorageService
    ) -> None:
        """Test that invalid path raises 403."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        path = "backups/other-user-id/latest.json"

        with pytest.raises(HTTPException) as exc_info:
            await service.presign_download(user_id, path, 900)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_presign_download_repository_error(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that repository errors are handled."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        path = f"backups/{user_id}/latest.json"

        mock_repository.create_signed_download_url.side_effect = Exception(
            "Supabase error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.presign_download(user_id, path, 900)

        assert exc_info.value.status_code == 500
        assert "Failed to create download URL" in exc_info.value.detail

