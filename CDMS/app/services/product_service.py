import json
from datetime import datetime
from typing import Any, List, Tuple, Union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.webhook import ProductSchema
from app.utils.logger import get_logger
from app.utils.helper import helper

logger = get_logger('app')

class ProductService:
    @staticmethod
    def normalize_product(item: Union[ProductSchema, dict]) -> dict:
        if isinstance(item, ProductSchema):
            data = item.model_dump()
        else:
            data = dict(item)

        raw_id = data.get("productId")
        external_id = str(raw_id).strip() if raw_id is not None else ""

        sku = str(data.get("sku", "")).strip()
        partner_sku = str(data.get("parentSKU", "")).strip()
        product_name = str(data.get("productName", "")).strip()

        return {
            "external_id": external_id,
            "sku": sku,
            "parentSKU": partner_sku,
            "productName": product_name,
            "assetType": data.get("assetType"),
            "hasSerial": bool(data.get("hasSerial", False)),
            "hasExpiration": bool(data.get("hasExpiration", False)),
            "color": data.get("color"),
            "size": data.get("size"),
            "description": data.get("description"),
            "units": helper.as_json_string(data.get("units")),
            "categories": helper.as_json_string(data.get("categories")),
            "isActive": bool(data.get("isActive", True)),
            "updatedAt": datetime.now(),
        }

    @classmethod
    def validate_and_normalize_payload(
        cls, raw_payload: Any
    ) -> Tuple[List[dict], int, List[str]]:
        raw_items: List[Any] = []

        if isinstance(raw_payload, list):
            raw_items = raw_payload
        elif isinstance(raw_payload, dict):
            raw_items = [raw_payload]
        else:
            return [], 0, ["Invalid payload type: expected dict or list."]

        total_received = len(raw_items)
        normalized_rows: List[dict] = []
        errors: List[str] = []

        for idx, item in enumerate(raw_items):
            try:
                if isinstance(item, ProductSchema):
                    validated_item = item
                else:
                    validated_item = ProductSchema(**item)

                normalized = cls.normalize_product(validated_item)
                normalized_rows.append(normalized)
            except Exception as e:
                err_msg = f"Item at index {idx} validation failed: {str(e)}"
                logger.warning(f"[ProductService] Error validate product: {err_msg}")
                errors.append(err_msg)

        return normalized_rows, total_received, errors

    @classmethod
    def upsert_products(cls, db: Session, rows: List[dict]) -> dict:
        if not rows:
            return {
                "upserted": 0,
                "deduplicated": 0,
            }

        dedup_map: dict[str, dict] = {}
        for row in rows:
            external_id = row["external_id"]
            dedup_map[external_id] = row

        rows_to_upsert = list(dedup_map.values())
        dedup_count = len(rows) - len(rows_to_upsert)

        stmt = insert(Product).values(rows_to_upsert)

        update_columns = {
            column.name: getattr(stmt.excluded, column.name)
            for column in Product.__table__.columns
            if column.name not in {"id", "external_id", "createdAt"}
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=[Product.external_id],
            set_=update_columns,
        )

        try:
            db.execute(stmt)
            db.commit()
            upserted_count = len(rows_to_upsert)
            logger.info(
                f"[ProductService] Upserted {upserted_count} - Deduplicated {dedup_count}."
            )
            return {
                "upserted": upserted_count,
                "deduplicated": dedup_count,
            }
        except Exception as exc:
            db.rollback()
            logger.error(f"[ProductService] Error during product upsert: {exc}", exc_info=True)
            raise
