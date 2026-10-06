from typing import Any, List, Union
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import config
from app.database import get_db
from app.schemas.webhook import (
    ProductSchema,
    WebhookResponse,
    WebhookResponseData,
)
from app.services.product_service import ProductService
from app.utils.auth import verify_webhook_token
from app.utils.logger import get_logger
from app.utils.rate_limiter import RateLimiter

logger = get_logger('app')

router = APIRouter(prefix="/webhook/sync", tags=["webhooks"])

# Rate limiter instance for webhook endpoint
webhook_rate_limiter = RateLimiter(
    times=config.WEBHOOK_RATE_LIMIT_TIMES,
    seconds=config.WEBHOOK_RATE_LIMIT_SECONDS,
    key_prefix="webhook_sync"
)


# @router.get("/", response_model=dict)
# async def init():
#     """Health check for webhook endpoint."""
#     return {
#         "code": 200,
#         "status": "ok",
#         "message": "Webhook service is running"
#     }


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Webhook sync products",
    description=""
)
async def emulatingCallbackClient(
    request: Request,
    response: Response,
    payload: Union[List[ProductSchema], ProductSchema, dict, list] = Body(...),
    db: Session = Depends(get_db),
    _: bool = Depends(webhook_rate_limiter),
    token: str = Depends(verify_webhook_token),
):
    logger.info(f"[Webhook] Received webhook request from {request.client.host if request.client else 'unknown'}")

    # Extract raw data if Pydantic model
    if isinstance(payload, ProductSchema):
        raw_data = payload.model_dump()
    elif isinstance(payload, list):
        raw_data = [item.model_dump() if isinstance(item, ProductSchema) else item for item in payload]
    else:
        raw_data = payload

    # Validate & normalize
    normalized_rows, total_received, errors = ProductService.validate_and_normalize_payload(raw_data)

    if total_received == 0:
        logger.warning("[Webhook] Empty payload received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "error": "Bad Request",
                "message": "Payload does not contain any product data."
            }
        )

    if not normalized_rows:
        logger.warning(f"[Webhook] All {total_received} items failed validation: {errors}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": 422,
                "error": "Validation Error",
                "message": "All items failed data validation.",
                "errors": errors
            }
        )

    # Upsert into DB
    try:
        upsert_result = ProductService.upsert_products(db, normalized_rows)
    except Exception as exc:
        logger.error(f"[Webhook] Database upsert failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "error": "Internal Server Error",
                "message": "Failed to persist product data to database."
            }
        )

    upserted_count = upsert_result.get("upserted", 0)
    deduplicated_count = upsert_result.get("deduplicated", 0)
    skipped_count = len(errors) + deduplicated_count

    return WebhookResponse(
        code=status.HTTP_200_OK,
        status="success",
        message=f"Successfully processed {upserted_count} products ({skipped_count} skipped/deduplicated).",
        data=WebhookResponseData(
            total_received=total_received,
            valid_items=len(normalized_rows),
            upserted=upserted_count,
            skipped=skipped_count,
            errors=errors
        )
    )