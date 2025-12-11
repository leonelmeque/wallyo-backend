"""JWT authentication and user validation."""

from typing import Optional
from fastapi import Header, HTTPException
from app.core.supabase import get_supabase_client
from app.core.logger import logger


def get_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and validate JWT from Authorization header.

    Returns the Supabase user ID (UUID) from the validated JWT.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        User ID (UUID string)

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        logger.warning("Authentication failed: Missing authorization header")
        raise HTTPException(
            status_code=401, detail="Missing authorization header"
        )
    
    if not authorization.lower().startswith("bearer "):
        logger.warning("Authentication failed: Invalid authorization header format (expected 'Bearer <token>')")
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format. Expected: Bearer <token>"
        )

    token = authorization.split(" ", 1)[1]
    
    if not token or not token.strip():
        logger.warning("Authentication failed: Empty token")
        raise HTTPException(
            status_code=401, detail="Empty token"
        )

    logger.debug("Validating JWT token with Supabase")

    try:
        # Use the shared Supabase client
        # getUser(token) validates the token server-side and returns user info
        client = get_supabase_client()
        response = client.auth.get_user(token)
        
        if not response.user:
            logger.warning("Authentication failed: Invalid token - no user found")
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = response.user.id
        logger.debug(f"Authentication successful - user_id: {user_id}")
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        JWT token string

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing authorization header"
        )
    
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format. Expected: Bearer <token>"
        )

    token = authorization.split(" ", 1)[1]
    
    if not token or not token.strip():
        raise HTTPException(
            status_code=401, detail="Empty token"
        )

    return token

