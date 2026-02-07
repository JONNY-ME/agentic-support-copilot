from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
import redis as redis_lib

async def check_postgres(database_url: str) -> Tuple[bool, str]:
    if not database_url:
        return False, "DATABASE_URL not provided"
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"
    
async def check_redis(redis_url: str) -> Tuple[bool, str]:
    if not redis_url:
        return False, "REDIS_URL not provided"
    try:
        client = redis_lib.from_url(redis_url, decode_responses=True)
        client.ping()
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"