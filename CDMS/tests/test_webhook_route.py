import unittest
from fastapi.testclient import TestClient
import asyncio
import httpx

from app.config import config
from app.database import SessionLocal
from app.main import app
from app.models.product import Product


class TestWebhookRoute(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_headers = {
            "Authorization": f"Bearer {config.WEBHOOK_AUTH_TOKEN}"
        }
        cls.auth_token = config.WEBHOOK_AUTH_TOKEN
        cls.test_external_ids = ["10000", "10001", "10002"]
        cls.db = SessionLocal()

    def setUp(self):
        from app.utils.rate_limiter import get_redis_client
        r = get_redis_client()
        if r:
            r.delete("ratelimit:webhook_sync:testclient")

    def tearDown(self):
        try:
            self.db.query(Product).filter(Product.external_id.in_(self.test_external_ids)).delete(synchronize_session=False)
            self.db.commit()
        finally:
            self.db.close()

    def test_webhook_unauthorized_no_token(self):
        res = self.client.post("/v1/webhook/sync/", json={"productId": 10000, "sku": "SUK001", "productName": "P1"})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Missing or invalid Authorization header")

    def test_webhook_unauthorized_wrong_token(self):
        headers = {"Authorization": "Bearer abcxyz"}
        res = self.client.post("/v1/webhook/sync/", json={"productId": 10000, "sku": "SUK001", "productName": "P1"}, headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid or expired token")

    def test_webhook_empty_payload(self):
        res = self.client.post("/v1/webhook/sync/", json=[], headers=self.auth_headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"]["code"], 400)

    def test_webhook_invalid_payload(self):
        invalid_body = {
            "productId": None,
            "sku": "",
            "productName": ""
        }
        res = self.client.post("/v1/webhook/sync/", json=invalid_body, headers=self.auth_headers)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["detail"]["code"], 422)

    def test_webhook_valid_single_product(self):
        body = {
            "productId": 10000,
            "sku": "UNIT_TEST_SKU_1",
            "parentSKU": "PARTNER_1",
            "productName": "Sản phẩm Unit Test 1",
            "assetType": "Single",
            "hasSerial": True,
            "hasExpiration": False,
            "color": "Blue",
            "size": "M",
            "description": "Test product",
            "units": ["pcs"],
            "categories": [{"categoryCode": "ELT", "categoryName": "Electronics"}],
            "isActive": True
        }
        res = self.client.post("/v1/webhook/sync/", json=body, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data["code"], 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["total_received"], 1)
        self.assertEqual(data["data"]["upserted"], 1)

        p = self.db.query(Product).filter(Product.external_id == "10000").first()
        self.assertIsNotNone(p)
        self.assertEqual(p.sku, "UNIT_TEST_SKU_1")
        self.assertEqual(p.productName, "Sản phẩm Unit Test 1")
        self.db.close()

    def test_webhook_valid_batch_products(self):
        body = [
            {
                "productId": 10001,
                "sku": "UNIT_TEST_SKU_2",
                "productName": "Sản phẩm Unit Test 2",
            },
            {
                "productId": 10002,
                "sku": "UNIT_TEST_SKU_3",
                "productName": "Sản phẩm Unit Test 3",
            }
        ]
        res = self.client.post("/v1/webhook/sync/", json=body, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data["data"]["total_received"], 2)
        self.assertEqual(data["data"]["upserted"], 2)

    def test_webhook_rate_limit_exceeded(self):
        body = {"productId": 10000, "sku": "S1", "productName": "P1"}
        # Make requests up to the limit
        for _ in range(config.WEBHOOK_RATE_LIMIT_TIMES):
            res = self.client.post("/v1/webhook/sync/", json=body, headers=self.auth_headers)
            self.assertEqual(res.status_code, 200)

        # The next request must be rejected with 429
        res_limit = self.client.post("/v1/webhook/sync/", json=body, headers=self.auth_headers)
        self.assertEqual(res_limit.status_code, 429)
        self.assertIn("Retry-After", res_limit.headers)
        self.assertEqual(res_limit.headers.get("X-RateLimit-Remaining"), "0")

    async def test_high_contention_race_condition_on_same_product(self):
        transport = httpx.ASGITransport(app=app)
        target_external_id = "RC_00000"
        num_concurrent = 10

        try:
            initial = Product(
                external_id=target_external_id,
                sku="SKU_RC_0001",
                productName="Initial Race Product",
                color="Red",
                isActive=True
            )
            self.db.add(initial)
            self.db.commit()
        finally:
            self.db.close()

        # Concurrently fire 10 updates to the same row from different IPs
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            tasks = []
            for i in range(num_concurrent):
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Forwarded-For": f"10.1.1.{i + 1}",
                }
                payload = {
                    "productId": target_external_id,
                    "sku": f"SKU_RC_{i}",
                    "productName": f"Race Updated Product {i}",
                    "color": f"Color_{i}",
                    "size": f"Size_{i}"
                }
                tasks.append(ac.post("/v1/webhook/sync/", json=payload, headers=headers))

            responses = await asyncio.gather(*tasks)

        # All 10 concurrent requests must succeed without deadlocks
        for _, resp in enumerate(responses):
            self.assertEqual(resp.status_code, 200)

        try:
            products = self.db.query(Product).filter(Product.external_id == target_external_id).all()
            self.assertEqual(len(products), 1)
        finally:
            self.db.close()


if __name__ == "__main__":
    unittest.main()
