"""Tests for storage schemas."""

import pytest
from pydantic import ValidationError

from app.features.storage.schemas import (
    PresignUploadReq,
    PresignUploadRes,
    PresignDownloadReq,
    PresignDownloadRes,
)


class TestPresignUploadReq:
    """Test PresignUploadReq schema."""

    def test_valid_upload_request(self) -> None:
        """Test that valid filename is accepted."""
        req = PresignUploadReq(filename="wallyo.db.enc")
        assert req.filename == "wallyo.db.enc"

    def test_missing_filename_raises_error(self) -> None:
        """Test that missing filename raises ValidationError."""
        with pytest.raises(ValidationError):
            PresignUploadReq()


class TestPresignUploadRes:
    """Test PresignUploadRes schema."""

    def test_valid_upload_response(self) -> None:
        """Test that valid response fields are accepted."""
        res = PresignUploadRes(
            path="backups/user-id/file.db.enc",
            token="token123",
            latest_path="backups/user-id/latest.json",
            latest_token="token456",
        )
        assert res.path == "backups/user-id/file.db.enc"
        assert res.token == "token123"
        assert res.latest_path == "backups/user-id/latest.json"
        assert res.latest_token == "token456"

    def test_missing_fields_raise_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            PresignUploadRes(path="backups/user-id/file.db.enc")


class TestPresignDownloadReq:
    """Test PresignDownloadReq schema."""

    def test_valid_download_request(self) -> None:
        """Test that valid path and seconds are accepted."""
        req = PresignDownloadReq(
            path="backups/user-id/latest.json", seconds=300
        )
        assert req.path == "backups/user-id/latest.json"
        assert req.seconds == 300

    def test_default_seconds(self) -> None:
        """Test that seconds defaults to 900."""
        req = PresignDownloadReq(path="backups/user-id/latest.json")
        assert req.seconds == 900

    def test_seconds_below_minimum_raises_error(self) -> None:
        """Test that seconds < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            PresignDownloadReq(path="backups/user-id/latest.json", seconds=0)

    def test_seconds_above_maximum_raises_error(self) -> None:
        """Test that seconds > 3600 raises ValidationError."""
        with pytest.raises(ValidationError):
            PresignDownloadReq(
                path="backups/user-id/latest.json", seconds=4000
            )

    def test_missing_path_raises_error(self) -> None:
        """Test that missing path raises ValidationError."""
        with pytest.raises(ValidationError):
            PresignDownloadReq()


class TestPresignDownloadRes:
    """Test PresignDownloadRes schema."""

    def test_valid_download_response(self) -> None:
        """Test that valid URL is accepted."""
        res = PresignDownloadRes(url="https://signed-url.example.com")
        assert res.url == "https://signed-url.example.com"

    def test_missing_url_raises_error(self) -> None:
        """Test that missing URL raises ValidationError."""
        with pytest.raises(ValidationError):
            PresignDownloadRes()

