from typing import Dict, Any, Optional
from storage3.types import SignedUploadURL
from supabase import StorageException, create_client
from app.core.logger import logger
import os


class StorageRepository:
    def __init__(self, bucket_name: str = "") -> None:
        self.bucket_name = bucket_name or os.getenv("SUPABASE_BACKUP_BUCKET", "user-backups")
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
            exists, existing_url = self.object_exists(path, user_token)
            if exists and existing_url:
                logger.info(
                    f"Object already exists for path: {path}; returning existing signed URL"
                )
                return existing_url

            result = supabase.storage.from_(self.bucket_name).create_signed_upload_url(
                path
            )
            self.__check_for_errors_in_create_signed_upload_result(result)
            return result
        except StorageException as e:
            error_detail = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))

            if (
                error_code == "Duplicate"
                or "already exists" in error_message.lower()
                and path.endswith("latest.json")
            ):
                logger.info(
                    f"File {path} already exists - this is expected for latest.json, returning success"
                )
                return {
                    "token": "file_already_exists",
                    "path": path,
                }

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

        if probe.get("error"):
            error_detail = probe.get("error", {})
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))
            if (
                error_code == "NoSuchKey"
                or "does not exist" in error_message
                or "not found" in error_message.lower()
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
        if result.get("error"):
            error_detail = result.get("error", {})
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))
            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = (
                    f"RLS policy violation: {error_message}. "
                    f"You need to create RLS policies on storage.objects table. "
                    f"Go to Supabase Dashboard > SQL Editor and run the policies SQL. "
                    f"See the README or documentation for the required SQL."
                )
            elif (
                "does not exist" in error_message
                or error_code == "NoSuchBucket"
                or error_code == "InvalidRequest"
            ):
                error_msg = (
                    f"Bucket '{self.bucket_name}' does not exist or is not accessible. "
                    f"Please verify it exists in Supabase Dashboard: Storage > Buckets"
                )
            elif error_code == "NoSuchKey":
                error_msg = f"File not found at path: {path}"
            else:
                error_msg = (
                    f"Error creating signed URL: {error_message} (code: {error_code})"
                )
            logger.error(f"Storage error: {error_msg}")
            raise Exception(error_msg)
        return result

    def __check_for_errors_in_create_signed_upload_result(
        self, result: SignedUploadURL
    ):
        if result.get("error"):
            error_detail = result.get("error", {})
            error_message = error_detail.get("message", "Unknown error")
            error_code = error_detail.get("error", error_detail.get("code", "Unknown"))

            if "row-level security policy" in error_message or "RLS" in error_message:
                error_msg = (
                    f"RLS policy violation: {error_message}. "
                    f"You need to create RLS policies on storage.objects table. "
                    f"Go to Supabase Dashboard > SQL Editor and run the policies SQL. "
                    f"See the README or documentation for the required SQL."
                )
            elif (
                "does not exist" in error_message
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
