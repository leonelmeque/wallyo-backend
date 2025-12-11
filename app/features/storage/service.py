"""Service layer for storage operations."""

import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException
from urllib.parse import parse_qs, urlparse
from app.core.logger import logger
from app.features.storage.repository import StorageRepository
from app.features.storage.schemas import PresignUploadRes, PresignDownloadRes


class StorageService:
    """Service for storage operations with business logic."""

    def __init__(self, repository: StorageRepository) -> None:
        """
        Initialize storage service.

        Args:
            repository: StorageRepository instance
        """
        self.repository = repository

    def build_backup_paths(self, user_id: str, filename: str) -> Tuple[str, str]:
        """
        Build backup file paths for a user.

        Args:
            user_id: Supabase user UUID
            filename: Original filename (e.g., "wallyo.db.enc")

        Returns:
            Tuple of (data_path, latest_path)
        """
        # Sanitize filename - replace slashes with underscores
        safe_filename = filename.replace("/", "_")

        # Generate ISO timestamp with colons replaced by hyphens
        timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-")

        # Generate random hex string (4 bytes = 8 hex characters)
        random_hex = secrets.token_hex(4)

        # Build data path
        if safe_filename.endswith(".db.enc"):
            data_path = f"{user_id}/{timestamp}-{random_hex}.db.enc"
        else:
            # For other file types, append the original extension
            data_path = f"{user_id}/{timestamp}-{random_hex}-{safe_filename}"

        # Build latest.json path
        latest_path = f"{user_id}/latest.json"

        return data_path, latest_path

    def validate_download_path(self, path: str, user_id: str) -> None:
        """
        Validate that a download path belongs to the user.

        Args:
            path: Path to validate
            user_id: Expected user ID

        Raises:
            HTTPException: 403 if path doesn't belong to user
        """
        expected_prefix = f"{user_id}/"
        if not path.startswith(expected_prefix):
            logger.warning(
                f"Path validation failed - user_id: {user_id}, path: {path}, expected prefix: {expected_prefix}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Path must start with {expected_prefix}",
            )

    async def presign_upload(
        self, user_id: str, filename: str, user_token: Optional[str] = None
    ) -> PresignUploadRes:
        """
        Generate presigned upload URLs for backup file and manifest.

        Args:
            user_id: Supabase user UUID
            filename: Original filename (e.g., "wallyo.db.enc")
            user_token: User's JWT token for RLS policy evaluation

        Returns:
            PresignUploadRes with paths and tokens

        Raises:
            HTTPException: 500 if Supabase operations fail
        """
        # Validate filename doesn't contain slashes
        if "/" in filename:
            logger.warning(
                f"Invalid filename - user_id: {user_id}, filename: {filename} (contains slashes)"
            )
            raise HTTPException(
                status_code=400, detail="Filename cannot contain slashes"
            )

        # Build paths
        data_path, latest_path = self.build_backup_paths(user_id, filename)
        logger.debug(
            f"Built backup paths - user_id: {user_id}, data_path: {data_path}, latest_path: {latest_path}"
        )

        try:
            # Create signed upload URLs
            logger.debug(
                f"Creating signed upload URLs - user_id: {user_id}, data_path: {data_path}"
            )
            upload_result = self.repository.create_signed_upload_url(
                data_path, user_token
            )
            latest_result = {}
            try:
                latest_result = self.repository.create_signed_upload_url(
                    latest_path, user_token
                )
            except Exception:
                pass

            logger.debug(
                f"Signed upload URLs created successfully - user_id: {user_id}"
            )

            upload_token = self._extract_upload_token(upload_result)
            latest_token = self._extract_upload_token(latest_result)

            return PresignUploadRes(
                path=data_path,
                token=upload_token,
                latest_path=latest_path,
                latest_token=latest_token,
            )

        except Exception as e:
            logger.error(
                f"Failed to create upload tokens - user_id: {user_id}, filename: {filename}, error: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create upload tokens: {str(e)}",
            )

    async def presign_download(
        self, user_id: str, path: str, seconds: int, user_token: Optional[str] = None
    ) -> PresignDownloadRes:
        """
        Generate presigned download URL for a storage object.

        Args:
            user_id: Supabase user UUID
            path: Path to the object
            seconds: URL validity duration
            user_token: User's JWT token for RLS policy evaluation

        Returns:
            PresignDownloadRes with signed URL

        Raises:
            HTTPException: 403 if path doesn't belong to user, 500 if Supabase fails
        """
        # Validate path belongs to user
        self.validate_download_path(path, user_id)

        try:
            # Create signed download URL
            logger.debug(
                f"Creating signed download URL - user_id: {user_id}, path: {path}, seconds: {seconds}"
            )
            result = self.repository.create_signed_download_url(
                path, seconds, user_token
            )
            logger.debug(
                f"Signed download URL created successfully - user_id: {user_id}, path: {path}"
            )

            return PresignDownloadRes(url=result["signedURL"])

        except Exception as e:
            logger.error(
                f"Failed to create download URL - user_id: {user_id}, path: {path}, error: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create download URL: {str(e)}",
            )

    @staticmethod
    def _extract_upload_token(result: dict) -> Optional[str]:
        if not isinstance(result, dict):
            return None
        if "token" in result:
            value = result.get("token")
            return value if isinstance(value, str) else None
        signed_url = result.get("signed_url") or result.get("signedURL")
        if not signed_url:
            return None
        parsed = urlparse(signed_url)
        tokens = parse_qs(parsed.query).get("token")
        return tokens[0] if tokens else None
