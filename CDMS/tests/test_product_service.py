import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from app.models.product import Product
from app.schemas.webhook import ProductSchema
from app.services.product_service import ProductService

class TestProductService(unittest.TestCase):
    def setUp(self):
        self.valid_product_dict = {
            "productId": "10001",
            "sku": "SKU10001",
            "parentSKU": "PR10001",
            "productName": "Product A",
            "assetType": "Single",
            "hasSerial": True,
            "hasExpiration": False,
            "color": "Red",
            "size": "L",
            "description": "Desc",
            "units": ["pcs"],
            "categories": [{"categoryCode": "ELT", "categoryName": "Electronics"}],
            "isActive": True,
        }

    def test_normalize_product_from_dict(self):
        normalized = ProductService.normalize_product(self.valid_product_dict)

        self.assertEqual(normalized["external_id"], "10001")
        self.assertEqual(normalized["sku"], "SKU10001")
        self.assertEqual(normalized["parentSKU"], "PR10001")
        self.assertEqual(normalized["productName"], "Product A")
        self.assertEqual(normalized["assetType"], "Single")
        self.assertTrue(normalized["hasSerial"])
        self.assertFalse(normalized["hasExpiration"])
        self.assertEqual(normalized["color"], "Red")
        self.assertEqual(normalized["size"], "L")
        self.assertEqual(normalized["description"], "Desc")
        self.assertEqual(normalized["units"], json.dumps(["pcs"], ensure_ascii=False))
        self.assertTrue(normalized["isActive"])
        self.assertIsInstance(normalized["updatedAt"], datetime)

    def test_validate_and_normalize_payload_single_dict(self):
        rows, total, errors = ProductService.validate_and_normalize_payload(self.valid_product_dict)

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(rows[0]["external_id"], "10001")

    def test_validate_and_normalize_payload_more_than_one(self):
        item2 = dict(self.valid_product_dict)
        item2["productId"] = "10002"
        item2["sku"] = "SKU10002"
        item2["productName"] = "Product B"

        payload = [self.valid_product_dict, item2]
        rows, total, errors = ProductService.validate_and_normalize_payload(payload)

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(rows[0]["external_id"], "10001")
        self.assertEqual(rows[1]["external_id"], "10002")

    def test_validate_and_normalize_payload_invalid_type(self):
        rows, total, errors = ProductService.validate_and_normalize_payload("this_is_string")

        self.assertEqual(total, 0)
        self.assertEqual(len(rows), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("Invalid payload type", errors[0])

    def test_validate_and_normalize_payload_with_errors(self):
        invalid_item = {
            "productId": None,
            "sku": "",
            "productName": "",
        }
        payload = [self.valid_product_dict, invalid_item]
        rows, total, errors = ProductService.validate_and_normalize_payload(payload)

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("validation failed", errors[0])

    def test_upsert_products_empty(self):
        db_mock = MagicMock()
        result = ProductService.upsert_products(db_mock, [])

        self.assertEqual(result, {"upserted": 0, "deduplicated": 0})
        db_mock.execute.assert_not_called()
        db_mock.commit.assert_not_called()

    def test_upsert_products_success(self):
        db_mock = MagicMock()
        row = ProductService.normalize_product(self.valid_product_dict)

        result = ProductService.upsert_products(db_mock, [row])

        self.assertEqual(result["upserted"], 1)
        self.assertEqual(result["deduplicated"], 0)
        db_mock.execute.assert_called_once()
        db_mock.commit.assert_called_once()

    def test_upsert_products_deduplication(self):
        db_mock = MagicMock()
        row1 = ProductService.normalize_product(self.valid_product_dict)
        row2 = dict(row1)
        row2["productName"] = "Product A updated"

        # Cùng external_id = "10001"
        result = ProductService.upsert_products(db_mock, [row1, row2])

        self.assertEqual(result["upserted"], 1)
        self.assertEqual(result["deduplicated"], 1)
        db_mock.execute.assert_called_once()
        db_mock.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
