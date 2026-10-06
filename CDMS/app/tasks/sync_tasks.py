import json

import httpx
from sqlalchemy.dialects.postgresql import insert
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import config
from app.models.product import Product
from app.services.product_service import ProductService
from app.tasks.celery_app import app
from app.utils.helper import helper

UPSERT_BATCH_SIZE = 1000
PAGE_SIZE = 50
REQUEST_TIMEOUT = 30


def normalize_vietful_product(raw: dict) -> dict | None:
    product_id = raw.get("productId")
    sku = raw.get("sku")
    product_name = raw.get("productName")
    if product_id is None or not sku or not product_name:
        return None

    return {
        "external_id": str(product_id),
        "sku": sku,
        "parentSKU": raw.get("parentSKU"),
        "productName": product_name,
        "assetType": raw.get("assetType"),
        "hasSerial": bool(raw.get("hasSerial", False)),
        "hasExpiration": bool(raw.get("hasExpiration", False)),
        "color": raw.get("color"),
        "size": raw.get("size"),
        "description": raw.get("description"),
        "units": helper.as_json_string(raw.get("units")),
        "categories": helper.as_json_string(raw.get("categories")),
        "isActive": bool(raw.get("isActive", True)),
    }


def fetch_vietful_products(client: httpx.Client, page_index: int, page_size: int) -> list[dict]:
    response = client.get(
        config.VIETFUL_API_URL,
        params={"PageIndex": page_index, "PageSize": page_size},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, dict):
        error_message = payload.get("errorMessage")
        if error_message:
            raise RuntimeError(f"Vietful API error: {error_message}")
        return []

    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected Vietful API payload type: {type(payload)}")

    return payload


def flush_batch(batch: list[dict], db: Session = Depends(get_db)) -> int:
    total_upserted = 0
    
    while batch:
        chunk = batch[:UPSERT_BATCH_SIZE]
        
        result = ProductService.upsert_products(db, chunk)
        total_upserted += result.get("upserted", 0)
        
        del batch[:UPSERT_BATCH_SIZE]
        
    return total_upserted


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_vietful_product_data(self):
    headers = {
        "Authorization": f"Bearer {config.VIETFUL_API_AUTH_TOKEN}"
    }

    try:
        print(f"[CELERY] Start sync products from {config.VIETFUL_API_URL}")
        page_index = 1
        fetched_count = 0
        upserted_count = 0
        skipped_count = 0
        batch: list[dict] = []

        with httpx.Client(headers=headers) as client:
            while True:
                page_items = fetch_vietful_products(client, page_index, PAGE_SIZE)
                if not page_items:
                    break

                for item in page_items:
                    normalized = normalize_vietful_product(item)
                    if normalized is None:
                        skipped_count += 1
                        continue
                    batch.append(normalized)
                    fetched_count += 1

                upserted_count += flush_batch(batch)

                if len(page_items) < PAGE_SIZE:
                    break
                page_index += 1

        if batch:
            upserted_count += ProductService.upsert_products(batch)

        result = {
            "pages": page_index,
            "fetched": fetched_count,
            "skipped": skipped_count,
            "upserted": upserted_count,
        }
        print(f"[CELERY SUCCESS] Sync products done: {result}")
        return result

    except Exception as exc:
        print(f"[CELERY ERROR] Lỗi khi sync product: {exc}")
        raise self.retry(exc=exc)
