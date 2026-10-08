from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router as api_router
from app.core.config import settings
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.CERTIFICATE_OUTPUT_DIR, exist_ok=True)
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
