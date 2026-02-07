from fastapi import APIRouter
import os 

from app.core.checks import check_postgres, check_redis

router = APIRouter()

@router.get("/health")
async def health():
    db_ok, db_msg = await check_postgres(os.getenv("DATABASE_URL", ""))
    redis_ok, redis_msg = await check_redis(os.getenv("REDIS_URL", ""))

    status = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "database": {"status": "ok" if db_ok else "error", "message": db_msg},
        "redis": {"status": "ok" if redis_ok else "error", "message": redis_msg},
    }