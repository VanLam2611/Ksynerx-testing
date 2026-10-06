import asyncio
import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException, Request

from app.utils.rate_limiter import RateLimiter, get_client_ip


class MockClient:
    def __init__(self, host):
        self.host = host


class MockURL:
    def __init__(self, path="/v1/webhook/sync/"):
        self.path = path


class MockRequest:
    def __init__(self, headers=None, client_host=None, path="/v1/webhook/sync/"):
        self.headers = headers or {}
        self.client = MockClient(client_host) if client_host else None
        self.url = MockURL(path)
        self.state = MagicMock()


class TestRateLimiter(unittest.TestCase):
    def test_get_client_ip_forwarded_for(self):
        req = MockRequest(headers={"X-Forwarded-For": "210.1.1.220, 45.1.1.1"})
        self.assertEqual(get_client_ip(req), "210.1.1.220")

    def test_get_client_ip_real_ip(self):
        req = MockRequest(headers={"X-Real-IP": "45.1.1.1"})
        self.assertEqual(get_client_ip(req), "45.1.1.1")

    def test_rate_limiter_exceeded(self):
        limiter = RateLimiter(times=2, seconds=10, key_prefix="test_unit_limit")
        req = MockRequest(client_host="10.0.0.10")

        res1 = asyncio.run(limiter(req))
        self.assertTrue(res1)

        res2 = asyncio.run(limiter(req))
        self.assertTrue(res2)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(limiter(req))

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Retry-After", ctx.exception.headers)
        self.assertEqual(ctx.exception.headers["X-RateLimit-Limit"], "2")
        self.assertEqual(ctx.exception.headers["X-RateLimit-Remaining"], "0")


if __name__ == "__main__":
    unittest.main()
