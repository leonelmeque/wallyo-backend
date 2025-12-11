"""Tests for JWT authentication."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from app.core.auth import get_user_id


class TestGetUserId:
    """Test get_user_id dependency function."""

    @pytest.mark.asyncio
    async def test_get_user_id_with_valid_token(self) -> None:
        """Test that valid JWT returns user ID."""
        mock_user = Mock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"

        mock_response = Mock()
        mock_response.user = mock_user

        mock_auth = Mock()
        mock_auth.set_session = Mock()
        mock_auth.get_user.return_value = mock_response

        mock_client = Mock()
        mock_client.auth = mock_auth

        with patch("app.core.auth.create_client", return_value=mock_client):
            user_id = await get_user_id("Bearer valid-token")

            assert user_id == "123e4567-e89b-12d3-a456-426614174000"
            mock_auth.set_session.assert_called_once_with(
                access_token="valid-token", refresh_token=""
            )
            mock_auth.get_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_id_with_missing_header(self) -> None:
        """Test that missing authorization header raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id(None)

        assert exc_info.value.status_code == 401
        assert "Missing or invalid authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_id_with_invalid_header_format(self) -> None:
        """Test that invalid header format raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id("InvalidFormat token")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_id_with_empty_bearer(self) -> None:
        """Test that empty bearer token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id("Bearer ")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_id_with_invalid_token(self) -> None:
        """Test that invalid token raises 401."""
        mock_response = Mock()
        mock_response.user = None

        mock_auth = Mock()
        mock_auth.set_session = Mock()
        mock_auth.get_user.return_value = mock_response

        mock_client = Mock()
        mock_client.auth = mock_auth

        with patch("app.core.auth.create_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_user_id("Bearer invalid-token")

            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_id_with_exception_from_supabase(self) -> None:
        """Test that Supabase client exceptions are handled."""
        mock_auth = Mock()
        mock_auth.set_session = Mock()
        mock_auth.get_user.side_effect = Exception("Connection error")

        mock_client = Mock()
        mock_client.auth = mock_auth

        with patch("app.core.auth.create_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_user_id("Bearer token")

            assert exc_info.value.status_code == 401
            assert "Token validation failed" in exc_info.value.detail

