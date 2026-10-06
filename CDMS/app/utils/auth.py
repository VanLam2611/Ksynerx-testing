import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import config
from app.utils.logger import get_logger

logger = get_logger('app')

security = HTTPBearer(auto_error=False)


async def verify_webhook_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    if not credentials or not credentials.credentials:
        logger.warning("[Auth] Webhook request missing or invalid Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    expected_token = config.WEBHOOK_AUTH_TOKEN

    if not expected_token or not secrets.compare_digest(token, expected_token):
        logger.warning("[Auth] Webhook request with invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"Authenticate": "Bearer"},
        )

    return token
