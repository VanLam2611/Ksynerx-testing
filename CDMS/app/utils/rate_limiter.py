import time
from collections import defaultdict
from typing import Optional
from fastapi import Request, HTTPException, status
import redis

from app.config import config
from app.utils.logger import get_logger

logger = get_logger('app')

redis_pool: Optional[redis.ConnectionPool] = None

def get_redis_client() -> Optional[redis.Redis]:
    global redis_pool
    try:
        if redis_pool is None:
            redis_pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
        client = redis.Redis(connection_pool=redis_pool)
        return client
    except Exception as e:
        logger.warning(f"[RateLimiter] Failed to initialize Redis client: {e}")
        return None


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    
    return "127.0.0.1"


class RateLimiter:
    def __init__(self, times: int = 60, seconds: int = 60, key_prefix: str = "webhook"):
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request):
        client_ip = get_client_ip(request)
        route_path = request.url.path
        rate_limit_key = f"ratelimit:{self.key_prefix}:{client_ip}"

        redis_client = get_redis_client()

        if redis_client:
            try:
                # Redis atomic transaction
                pipe = redis_client.pipeline()
                pipe.incr(rate_limit_key)
                pipe.ttl(rate_limit_key)
                current_requests, ttl = pipe.execute()

                if ttl == -1:
                    redis_client.expire(rate_limit_key, self.seconds)
                    ttl = self.seconds

                remaining = max(0, self.times - current_requests)

                request.state.rate_limit_limit = self.times
                request.state.rate_limit_remaining = remaining
                request.state.rate_limit_reset = ttl

                if current_requests > self.times:
                    logger.warning(
                        f"[RateLimiter] Rate limit exceeded for IP {client_ip} on {route_path}. "
                        f"Note: {current_requests}/{self.times}, TTL: {ttl}s"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "code": 429,
                            "error": "Too Many Requests",
                            "message": f"Rate limit exceeded. Maximum {self.times} requests per {self.seconds} seconds."
                        },
                        headers={
                            "Retry-After": str(max(ttl, 1)),
                            "X-RateLimit-Limit": str(self.times),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(ttl)
                        }
                    )
                return True

            except redis.RedisError as exc:
                logger.warning(f"[RateLimiter] Redis error: {exc}.")

        return True
