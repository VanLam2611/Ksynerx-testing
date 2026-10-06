import asyncio
import unittest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import config
from app.utils.auth import verify_webhook_token


class TestAuth(unittest.TestCase):
    def test_verify_token_missing_credentials(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verify_webhook_token(None))

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Missing or invalid Authorization header")

    def test_verify_token_invalid_token(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_token_123")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verify_webhook_token(creds))

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Invalid or expired token")

    def test_verify_token_valid(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=config.WEBHOOK_AUTH_TOKEN)
        result = asyncio.run(verify_webhook_token(creds))

        self.assertEqual(result, config.WEBHOOK_AUTH_TOKEN)


if __name__ == "__main__":
    unittest.main()
