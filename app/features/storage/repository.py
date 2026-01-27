from typing import Dict, Any, List, Optional
from storage3.types import SignedUploadURL
from supabase import StorageException, create_client
from app.core.logger import logger
import os


class StorageRepository:
    def __init__(self, bucket_name: str = "") -> None:
        self.bucket_name = bucket_name or os.getenv(
            "SUPABASE_BACKUP_BUCKET", "user-backups"
        )
        logger.debug(f"StorageRepository initialized with bucket: {self.bucket_name}")

    def _get_user_client(self, user_token: str):
        from app.core.config import get_settings

        s = get_settings()
        if not s.supabase_anon_key:
            error_msg = (
                "SUPABASE_ANON_KEY is required for storage operations with RLS. "
                "Please set it in your .env file. You can find it in Supabase Dashboard > API Settings."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.debug("Creating Supabase client with anon key and user token for RLS")
        client = create_client(s.supabase_url, s.supabase_anon_key)
        client.auth.set_session(access_token=user_token, refresh_token="")
        return client

    def create_signed_upload_url(
        self, path: str, user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        if user_token:
            supabase = self._get_user_client(user_token)
        else:
            from app.core.supabase import get_supabase_client

            supabase = get_supabase_client()
        logger.debug(
            f"Creating signed upload URL for path: {path} in bucket: {self.bucket_name}"
        )

        try:
            result = supabase.storage.from_(self.bucket_name).create_signed_upload_url(
                path
            )
            needs_retry = self.__check_for_errors_in_create_signed_upload_result(result)
            if needs_retry:
                # File already exists - delete and retry
                logger.info(f"File {path} already exists (from result) - deleting to allow overwrite")
                self.delete_files([path], user_token)
                result = supabase.storage.from_(self.bucket_name).create_signed_upload_url(path)
                self.__check_for_errors_in_create_signed_upload_result(result)
            return result
        except StorageException as e:
            error_detail = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
            error_message = str(error_detail.get("message", "")) if isinstance(error_detail, dict) else str(e)
            error_code = error_detail.get("error", error_detail.get("code", "Unknown")) if isinstance(error_detail, dict) else "Unknown"

            # Handle "already exists" - delete and retry to allow overwrite
            if error_code == "Duplicate" or "already exists" in error_message.lower():
                logger.info(f"File {path} already exists (from exception) - deleting to allow overwrite")
                self.delete_files([path], user_token)
                result = supabase.storage.from_(self.bucket_name).create_signed_upload_url(path)
                self.__check_for_errors_in_create_signed_upload_result(result)
                return result
            raise

    def object_exists(
        self, path: str, user_token: Optional[str] = None
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        if user_token:
            supabase = self._get_user_client(user_token)
        else:
            from app.core.supabase import get_supabase_client

            supabase = get_supabase_client()
        logger.debug(
            f"Checking object existence for path: {path} in bucket: {self.bucket_name}"
        )
        try:
            probe = supabase.storage.from_(self.bucket_name).create_signed_url(
                path=path, expires_in=120
            )
        except StorageException as e:
            error_detail = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))
            if (
                error_code == "NoSuchKey"
                or "does not exist" in error_message
                or "not found" in error_message.lower()
            ):
                logger.info(f"Object does not exist at path: {path}")
                return False, None
            raise

        if not probe:
            return False, None

        # Supabase returns error info at top level: {'statusCode': 404, 'error': 'not_found', 'message': 'Object not found'}
        if probe.get("error") or probe.get("statusCode"):
            error_message = probe.get("message", "Unknown error")
            error_code = probe.get("error", probe.get("code", "Unknown"))
            if (
                error_code == "NoSuchKey"
                or error_code == "not_found"
                or "does not exist" in str(error_message).lower()
                or "not found" in str(error_message).lower()
            ):
                logger.info(f"Object does not exist at path: {path}")
                return False, None
            raise Exception(
                f"Error checking existence: {error_message} (code: {error_code})"
            )

        return True, probe

    def create_signed_download_url(
        self, path: str, expires_in: int, user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        if user_token:
            supabase = self._get_user_client(user_token)
        else:
            from app.core.supabase import get_supabase_client

            supabase = get_supabase_client()
        logger.debug(
            f"Creating signed download URL for path: {path} in bucket: {self.bucket_name}, expires_in: {expires_in}s"
        )
        result = supabase.storage.from_(self.bucket_name).create_signed_url(
            path=path, expires_in=expires_in
        )
        # Supabase returns error info at top level: {'statusCode': 404, 'error': 'not_found', 'message': 'Object not found'}
        if result.get("error") or result.get("statusCode"):
            error_message = str(result.get("message", "Unknown error"))
            error_code = result.get("error", result.get("code", "Unknown"))
            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = (
                    f"RLS policy violation: {error_message}. "
                    f"You need to create RLS policies on storage.objects table. "
                    f"Go to Supabase Dashboard > SQL Editor and run the policies SQL. "
                    f"See the README or documentation for the required SQL."
                )
            elif error_code == "NoSuchBucket" or error_code == "InvalidRequest":
                error_msg = (
                    f"Bucket '{self.bucket_name}' does not exist or is not accessible. "
                    f"Please verify it exists in Supabase Dashboard: Storage > Buckets"
                )
            elif (
                error_code == "NoSuchKey"
                or error_code == "not_found"
                or "not found" in error_message.lower()
            ):
                error_msg = f"File not found at path: {path}"
            else:
                error_msg = (
                    f"Error creating signed URL: {error_message} (code: {error_code})"
                )
            logger.error(f"Storage error: {error_msg}")
            raise Exception(error_msg)
        return result

    def list_user_files(
        self, user_id: str, user_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all files in a user's storage directory.

        Args:
            user_id: Supabase user UUID (used as directory prefix)
            user_token: User's JWT token for RLS policy evaluation

        Returns:
            List of file objects with name, id, updated_at, created_at, metadata
        """
        if user_token:
            supabase = self._get_user_client(user_token)
        else:
            from app.core.supabase import get_supabase_client

            supabase = get_supabase_client()

        logger.debug(
            f"Listing files for user: {user_id} in bucket: {self.bucket_name}"
        )

        try:
            result = supabase.storage.from_(self.bucket_name).list(path=user_id)
            if isinstance(result, list):
                logger.debug(f"Found {len(result)} files for user: {user_id}")
                return result
            return []
        except StorageException as e:
            error_detail = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))

            # Empty directory or not found is not an error
            if (
                error_code == "NoSuchKey"
                or "not found" in error_message.lower()
                or "does not exist" in error_message.lower()
            ):
                logger.debug(f"No files found for user: {user_id}")
                return []

            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = f"RLS policy violation: {error_message}. Check storage policies."
            elif error_code == "NoSuchBucket" or "does not exist" in error_message:
                error_msg = f"Bucket '{self.bucket_name}' does not exist."
            else:
                error_msg = f"Error listing files: {error_message} (code: {error_code})"

            logger.error(f"Storage error: {error_msg}")
            raise Exception(error_msg)

    def delete_files(
        self, paths: List[str], user_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Delete multiple files from storage.

        Args:
            paths: List of full paths to delete (e.g., ["user_id/file1.db.enc"])
            user_token: User's JWT token for RLS policy evaluation

        Returns:
            List of deleted file objects
        """
        if not paths:
            return []

        if user_token:
            supabase = self._get_user_client(user_token)
        else:
            from app.core.supabase import get_supabase_client

            supabase = get_supabase_client()

        logger.debug(
            f"Deleting {len(paths)} files from bucket: {self.bucket_name}"
        )

        try:
            result = supabase.storage.from_(self.bucket_name).remove(paths)
            logger.debug(f"Successfully deleted {len(paths)} files")
            return result if isinstance(result, list) else []
        except StorageException as e:
            error_detail = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))

            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = f"RLS policy violation: {error_message}. Check storage policies."
            elif error_code == "NoSuchBucket" or "does not exist" in error_message:
                error_msg = f"Bucket '{self.bucket_name}' does not exist."
            else:
                error_msg = f"Error deleting files: {error_message} (code: {error_code})"

            logger.error(f"Storage error: {error_msg}")
            raise Exception(error_msg)

    def __check_for_errors_in_create_signed_upload_result(
        self, result: SignedUploadURL
    ) -> bool:
        """Check for errors in create_signed_upload_url result.

        Returns:
            True if "already exists" error (caller should delete and retry)
            False if no error

        Raises:
            Exception for other errors
        """
        # Handle top-level error structure from Supabase
        if result.get("error") or result.get("statusCode"):
            error_message = str(result.get("message", "Unknown error"))
            error_code = result.get("error", result.get("code", "Unknown"))

            # Signal to caller to delete and retry for duplicate files
            if error_code == "Duplicate" or "already exists" in error_message.lower():
                return True

            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = (
                    f"RLS policy violation: {error_message}. "
                    f"You need to create RLS policies on storage.objects table. "
                    f"Go to Supabase Dashboard > SQL Editor and run the policies SQL. "
                    f"See the README or documentation for the required SQL."
                )
            elif (
                "does not exist" in error_message.lower()
                or error_code == "NoSuchBucket"
                or error_code == "InvalidRequest"
            ):
                error_msg = (
                    f"Bucket '{self.bucket_name}' does not exist or is not accessible. "
                    f"Please verify it exists in Supabase Dashboard: Storage > Buckets"
                )
            else:
                error_msg = (
                    f"Error creating upload token: {error_message} (code: {error_code})"
                )
            logger.error(f"Storage error: {error_msg}")
            raise Exception(error_msg)
        return False
