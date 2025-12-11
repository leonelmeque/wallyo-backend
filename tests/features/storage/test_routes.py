"""Tests for storage routes."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.features.storage.routes import router
from app.features.storage.schemas import PresignUploadRes, PresignDownloadRes


# Create test app
app = FastAPI()
app.include_router(router)


class TestPresignUploadRoute:
    """Test POST /v1/storage/presign-upload route."""

    @patch("app.features.storage.routes._storage_service")
    def test_presign_upload_success(self, mock_service: Mock) -> None:
        """Test successful presign upload request."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_response = PresignUploadRes(
            path=f"backups/{user_id}/2025-12-06T11-20-45-a1b2c3.db.enc",
            token="token1",
            latest_path=f"backups/{user_id}/latest.json",
            latest_token="token2",
        )

        mock_service.presign_upload = AsyncMock(return_value=mock_response)

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-upload",
            json={"filename": "wallyo.db.enc"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "token" in data
        assert "latest_path" in data
        assert "latest_token" in data
        assert data["path"].endswith(".db.enc")
        assert data["latest_path"].endswith("latest.json")

    @patch("app.features.storage.routes.get_user_id")
    def test_presign_upload_missing_auth(self, mock_get_user_id: Mock) -> None:
        """Test that missing authorization header returns 401."""
        mock_get_user_id.side_effect = Exception("Unauthorized")

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-upload",
            json={"filename": "wallyo.db.enc"},
        )

        assert response.status_code in [401, 422]  # 422 if FastAPI validation fails first

    @patch("app.features.storage.routes._storage_service")
    def test_presign_upload_invalid_filename(self, mock_service: Mock) -> None:
        """Test that filename with slashes returns 400."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        from fastapi import HTTPException

        mock_service.presign_upload = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Filename cannot contain slashes")
        )

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-upload",
            json={"filename": "path/to/file.db.enc"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 400


class TestPresignDownloadRoute:
    """Test POST /v1/storage/presign-download route."""

    @patch("app.features.storage.routes._storage_service")
    def test_presign_download_success(self, mock_service: Mock) -> None:
        """Test successful presign download request."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_response = PresignDownloadRes(
            url="https://signed-url.example.com"
        )

        mock_service.presign_download = AsyncMock(return_value=mock_response)

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-download",
            json={
                "path": f"backups/{user_id}/latest.json",
                "seconds": 900,
            },
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["url"] == "https://signed-url.example.com"

    @patch("app.features.storage.routes._storage_service")
    def test_presign_download_with_default_seconds(
        self, mock_service: Mock
    ) -> None:
        """Test that seconds defaults to 900 if not provided."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_response = PresignDownloadRes(
            url="https://signed-url.example.com"
        )

        mock_service.presign_download = AsyncMock(return_value=mock_response)

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-download",
            json={"path": f"backups/{user_id}/latest.json"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        # Verify service was called with default seconds (900)
        mock_service.presign_download.assert_called_once()
        call_args = mock_service.presign_download.call_args
        assert call_args[0][2] == 900  # seconds parameter

    @patch("app.features.storage.routes._storage_service")
    def test_presign_download_invalid_path(self, mock_service: Mock) -> None:
        """Test that path for different user returns 403."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        from fastapi import HTTPException

        mock_service.presign_download = AsyncMock(
            side_effect=HTTPException(
                status_code=403, detail="Path must start with backups/{user_id}/"
            )
        )

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-download",
            json={
                "path": "backups/other-user-id/latest.json",
                "seconds": 900,
            },
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 403

    @patch("app.features.storage.routes.get_user_id")
    def test_presign_download_missing_auth(
        self, mock_get_user_id: Mock
    ) -> None:
        """Test that missing authorization header returns 401."""
        mock_get_user_id.side_effect = Exception("Unauthorized")

        client = TestClient(app)
        response = client.post(
            "/v1/storage/presign-download",
            json={"path": "backups/user-id/latest.json"},
        )

        assert response.status_code in [401, 422]

