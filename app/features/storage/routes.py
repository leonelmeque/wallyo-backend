"""API routes for storage feature."""

from fastapi import APIRouter, Depends
from app.core.auth import get_user_id, get_user_token
from app.core.logger import logger
from app.features.storage.repository import StorageRepository
from app.features.storage.service import StorageService
from app.features.storage.schemas import (
    PresignUploadReq,
    PresignUploadRes,
    PresignDownloadReq,
    PresignDownloadRes,
)

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])

def get_storage_service() -> StorageService:
    repository = StorageRepository()
    return StorageService(repository)


@router.post("/presign-upload", response_model=PresignUploadRes)
async def presign_upload(
    body: PresignUploadReq,
    user_id: str = Depends(get_user_id),
    user_token: str = Depends(get_user_token),
    service: StorageService = Depends(get_storage_service),
) -> PresignUploadRes:
    logger.info(f"Presign upload request received - user_id: {user_id}, filename: {body.filename}")
    try:
        result = await service.presign_upload(user_id, body.filename, user_token)
        logger.info(f"Presign upload successful - user_id: {user_id}, path: {result.path}")
        return result
    except Exception as e:
        logger.error(f"Presign upload failed - user_id: {user_id}, filename: {body.filename}, error: {str(e)}")
        raise


@router.post("/presign-download", response_model=PresignDownloadRes)
async def presign_download(
    body: PresignDownloadReq,
    user_id: str = Depends(get_user_id),
    user_token: str = Depends(get_user_token),
    service: StorageService = Depends(get_storage_service),
) -> PresignDownloadRes:
    logger.info(f"Presign download request received - user_id: {user_id}, path: {body.path}, seconds: {body.seconds}")
    try:
        result = await service.presign_download(
            user_id, body.path, body.seconds, user_token
        )
        logger.info(f"Presign download successful - user_id: {user_id}, path: {body.path}")
        return result
    except Exception as e:
        logger.error(f"Presign download failed - user_id: {user_id}, path: {body.path}, error: {str(e)}")
        raise
