"""Service layer for storage operations."""

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from urllib.parse import parse_qs, urlparse
from app.core.logger import logger
from app.features.storage.repository import StorageRepository
from app.features.storage.schemas import PresignUploadRes, PresignDownloadRes

# Backup cleanup constants
MAX_BACKUPS = 3  # Cleanup triggers when user has this many or more
KEEP_BACKUPS = 2  # Number of backups to keep after cleanup


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

    def _sort_backups_by_timestamp(
        self, backup_files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sort backup files by timestamp extracted from filename.

        Args:
            backup_files: List of file objects with 'name' field

        Returns:
            List sorted by timestamp (oldest first)

        Filename format: {ISO-timestamp}-{random-hex}.db.enc
        Example: 2025-01-26T12-30-45.123456+00-00-a1b2c3d4.db.enc
        """

        def extract_timestamp(file_obj: Dict[str, Any]) -> str:
            name = file_obj.get("name", "")
            try:
                # Remove .db.enc suffix and the random hex (last 8 chars after hyphen)
                base = name.rsplit(".db.enc", 1)[0]
                parts = base.rsplit("-", 1)
                if len(parts) == 2 and len(parts[1]) == 8:
                    return parts[0]
                return base
            except Exception:
                return name

        return sorted(backup_files, key=extract_timestamp)

    async def cleanup_old_backups(
        self, user_id: str, user_token: Optional[str] = None
    ) -> int:
        """
        Clean up old backups if user has MAX_BACKUPS or more .db.enc files.
        Deletes oldest files until only KEEP_BACKUPS remain.

        Args:
            user_id: Supabase user UUID
            user_token: User's JWT token for RLS policy evaluation

        Returns:
            Number of files deleted

        Note:
            This method catches all exceptions and logs them.
            It never raises exceptions to ensure the presign_upload flow continues.
        """
        try:
            # List all files in user's directory
            files = self.repository.list_user_files(user_id, user_token)

            # Filter to only .db.enc files (exclude latest.json and other files)
            backup_files = [
                f for f in files if f.get("name", "").endswith(".db.enc")
            ]

            # Check if cleanup is needed
            if len(backup_files) < MAX_BACKUPS:
                logger.debug(
                    f"User {user_id} has {len(backup_files)} backups, no cleanup needed"
                )
                return 0

            # Sort by timestamp (oldest first)
            sorted_backups = self._sort_backups_by_timestamp(backup_files)

            # Determine files to delete (all except the KEEP_BACKUPS most recent)
            files_to_delete = sorted_backups[:-KEEP_BACKUPS]

            # Build full paths and delete
            paths_to_delete = [
                f"{user_id}/{f.get('name')}" for f in files_to_delete
            ]

            logger.info(
                f"Cleaning up {len(paths_to_delete)} old backups for user {user_id}"
            )
            self.repository.delete_files(paths_to_delete, user_token)

            return len(paths_to_delete)

        except Exception as e:
            # Log error but don't fail the presign_upload request
            logger.error(f"Failed to cleanup old backups for user {user_id}: {str(e)}")
            return 0

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

        # Clean up old backups before creating new one
        deleted_count = await self.cleanup_old_backups(user_id, user_token)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backups for user {user_id}")

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
