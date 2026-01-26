"""Tests for storage service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from app.features.storage.service import StorageService, MAX_BACKUPS, KEEP_BACKUPS
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


class TestBackupCleanup:
    """Tests for backup cleanup functionality."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create a mock repository."""
        return Mock(spec=StorageRepository)

    @pytest.fixture
    def service(self, mock_repository: Mock) -> StorageService:
        """Create a service instance with mock repository."""
        return StorageService(mock_repository)

    def test_sort_backups_by_timestamp_correct_order(
        self, service: StorageService
    ) -> None:
        """Test that backups are sorted by timestamp (oldest first)."""
        files = [
            {"name": "2025-01-26T12-30-45.123456+00-00-a1b2c3d4.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-deadbeef.db.enc"},
            {"name": "2025-01-27T08-15-30.999999+00-00-12345678.db.enc"},
        ]

        sorted_files = service._sort_backups_by_timestamp(files)

        assert sorted_files[0]["name"].startswith("2025-01-25")
        assert sorted_files[1]["name"].startswith("2025-01-26")
        assert sorted_files[2]["name"].startswith("2025-01-27")

    def test_sort_backups_by_timestamp_empty_list(
        self, service: StorageService
    ) -> None:
        """Test sorting empty list returns empty list."""
        result = service._sort_backups_by_timestamp([])
        assert result == []

    def test_sort_backups_by_timestamp_single_file(
        self, service: StorageService
    ) -> None:
        """Test sorting single file returns same file."""
        files = [{"name": "2025-01-26T12-00-00.000000+00-00-aabbccdd.db.enc"}]
        result = service._sort_backups_by_timestamp(files)
        assert len(result) == 1
        assert result[0] == files[0]

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_no_cleanup_needed(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that cleanup is skipped when user has less than MAX_BACKUPS."""
        user_id = "user-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-25T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "latest.json"},
        ]

        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 0
        mock_repository.delete_files.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_deletes_oldest(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that oldest backups are deleted when cleanup is triggered."""
        user_id = "user-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-23T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-24T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-cccccccc.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-dddddddd.db.enc"},
            {"name": "latest.json"},
        ]
        mock_repository.delete_files.return_value = []

        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 2  # 4 backups - KEEP_BACKUPS(2) = 2 deleted
        mock_repository.delete_files.assert_called_once()
        deleted_paths = mock_repository.delete_files.call_args[0][0]
        assert len(deleted_paths) == 2
        assert "2025-01-23" in deleted_paths[0]
        assert "2025-01-24" in deleted_paths[1]

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_ignores_latest_json(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that latest.json is not counted or deleted."""
        user_id = "user-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-25T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "latest.json"},
            {"name": "some-other-file.txt"},
        ]

        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 0  # Only 2 .db.enc files
        mock_repository.delete_files.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_exactly_max_backups(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test cleanup when user has exactly MAX_BACKUPS."""
        user_id = "user-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-24T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-cccccccc.db.enc"},
        ]
        mock_repository.delete_files.return_value = []

        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 1  # 3 backups - KEEP_BACKUPS(2) = 1 deleted
        deleted_paths = mock_repository.delete_files.call_args[0][0]
        assert "2025-01-24" in deleted_paths[0]

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_error_does_not_raise(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that cleanup errors don't fail the request."""
        user_id = "user-123"
        mock_repository.list_user_files.side_effect = Exception("Storage error")

        # Should not raise
        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_delete_error_does_not_raise(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that delete errors don't fail the request."""
        user_id = "user-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-24T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-cccccccc.db.enc"},
        ]
        mock_repository.delete_files.side_effect = Exception("Delete failed")

        # Should not raise
        deleted = await service.cleanup_old_backups(user_id)

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_with_user_token(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that user token is passed to repository methods."""
        user_id = "user-123"
        user_token = "jwt-token-123"
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-24T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-cccccccc.db.enc"},
        ]
        mock_repository.delete_files.return_value = []

        await service.cleanup_old_backups(user_id, user_token)

        mock_repository.list_user_files.assert_called_once_with(user_id, user_token)
        mock_repository.delete_files.assert_called_once()
        assert mock_repository.delete_files.call_args[0][1] == user_token

    @pytest.mark.asyncio
    async def test_presign_upload_calls_cleanup(
        self, service: StorageService, mock_repository: Mock
    ) -> None:
        """Test that presign_upload calls cleanup before generating URLs."""
        user_id = "user-123"
        filename = "wallyo.db.enc"

        # Setup: user has 3 backups (at MAX_BACKUPS)
        mock_repository.list_user_files.return_value = [
            {"name": "2025-01-24T10-00-00.000000+00-00-aaaaaaaa.db.enc"},
            {"name": "2025-01-25T10-00-00.000000+00-00-bbbbbbbb.db.enc"},
            {"name": "2025-01-26T10-00-00.000000+00-00-cccccccc.db.enc"},
        ]
        mock_repository.delete_files.return_value = []
        mock_repository.create_signed_upload_url.return_value = {"token": "test-token"}

        await service.presign_upload(user_id, filename)

        # Verify cleanup was called
        mock_repository.list_user_files.assert_called_once()
        mock_repository.delete_files.assert_called_once()

    def test_max_backups_constant(self) -> None:
        """Test MAX_BACKUPS constant value."""
        assert MAX_BACKUPS == 3

    def test_keep_backups_constant(self) -> None:
        """Test KEEP_BACKUPS constant value."""
        assert KEEP_BACKUPS == 2

