import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import config as _config  # noqa: F401
from app.api import router
from app.db import create_database_engine
from app.security import RateLimitMiddleware

app = FastAPI(
    title="ContextOS API",
    version="0.1.0",
    description="Deterministic implementation recovery service (portfolio prototype).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    try:
        with create_database_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database readiness check failed.") from exc


@app.get("/api/v1/environment")
def environment() -> dict[str, object]:
    mode = os.getenv("CONTEXTOS_ENV", "development")
    writes = os.getenv("DEMO_WRITE_ENABLED", "true" if mode == "development" else "false").lower() == "true"
    return {"environment": mode, "synthetic_data": True, "write_enabled": writes, "authentication": "demo_operator_only" if writes else "read_only"}

