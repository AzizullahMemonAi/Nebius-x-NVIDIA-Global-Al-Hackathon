"""
Nexora Backend Application
FastAPI application entry point
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from nexora.backend.app.api.routes import router as api_router
from nexora.backend.app.core.database import close_db, init_db
from nexora.backend.config.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    await init_db()
    
    # Start background worker
    # worker_task = asyncio.create_task(run_worker())
    
    yield
    
    # Shutdown
    # worker_task.cancel()
    # try:
    #     await worker_task
    # except asyncio.CancelledError:
    #     pass
    
    await close_db()


app = FastAPI(
    title="Nexora API",
    description="Secure, token-efficient adaptive coding agent",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api/v1")

# Mount frontend static files (in production)
# app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nexora",
        "version": "3.0.0",
        "description": "Secure, token-efficient adaptive coding agent",
        "docs": "/docs",
    }


@app.get("/api/v1/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "nexora.backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
