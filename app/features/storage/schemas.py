"""Pydantic schemas for storage feature."""

from pydantic import BaseModel, Field


class PresignUploadReq(BaseModel):
    """Request schema for presigning upload URLs."""

    filename: str = Field(
        ..., description="Filename for the backup (e.g., 'wallyo.db.enc')"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "filename": "wallyo.db.enc",
            }
        }


class PresignUploadRes(BaseModel):
    """Response schema for presigning upload URLs."""

    path: str = Field(..., description="Path for the encrypted DB file")
    token: str = Field(..., description="Signed upload token for the DB file")
    latest_path: str = Field(..., description="Path for the latest.json manifest")
    latest_token: str = Field(
        ..., description="Signed upload token for the latest.json manifest"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "path": "backups/123e4567-e89b-12d3-a456-426614174000/2025-12-06T11-20-45-a1b2c3.db.enc",
                "token": "signed-upload-token",
                "latest_path": "backups/123e4567-e89b-12d3-a456-426614174000/latest.json",
                "latest_token": "signed-upload-token",
            }
        }


class PresignDownloadReq(BaseModel):
    """Request schema for presigning download URLs."""

    path: str = Field(
        ...,
        description="Path to the object to download (must start with backups/<userId>/",
    )
    seconds: int = Field(
        default=900,
        ge=1,
        le=3600,
        description="URL validity duration in seconds (1-3600)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "path": "backups/123e4567-e89b-12d3-a456-426614174000/latest.json",
                "seconds": 900,
            }
        }


class PresignDownloadRes(BaseModel):
    """Response schema for presigning download URLs."""

    url: str = Field(..., description="Signed download URL")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "url": "https://signed-download-url",
            }
        }

