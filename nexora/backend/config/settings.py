"""
Nexora Backend Configuration
Centralized settings management using Pydantic Settings
"""
import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file="nexora/backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = "Nexora"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8001, description="Server port")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./nexora.db",
        description="Database connection string for local development"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")
    
    # Redis (for future queue implementation)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection string")
    
    # Security
    SECRET_KEY: str = Field(default="", description="Secret key for session signing")
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"],
        description="CORS allowed origins"
    )
    
    # Nebius / NVIDIA Provider
    NEBIUS_API_KEY: str = Field(default="", description="Nebius API key")
    NEBIUS_BASE_URL: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Nebius API base URL"
    )
    NEBIUS_TIMEOUT: int = Field(default=120, description="Provider request timeout in seconds")
    
    # Google Gemini (secondary provider -- additive only, never replaces Nebius)
    GEMINI_ENABLED: bool = Field(
        default=True,
        description="Register Gemini as a secondary provider. Nebius stays primary.",
    )
    GEMINI_API_KEY: str = Field(default="", description="Gemini API key")
    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        description="Gemini API base URL",
    )
    GEMINI_TIMEOUT: int = Field(default=180, description="Gemini request timeout in seconds")
    GEMINI_MAX_RETRIES: int = Field(default=3, description="Gemini attempts before giving up")
    GEMINI_RETRY_BASE_DELAY: float = Field(
        default=2.0,
        description="First backoff in seconds between Gemini retries; doubles each attempt",
    )
    GEMINI_RATE_LIMIT_BASE_DELAY: float = Field(
        default=10.0,
        description="Backoff base for HTTP 429, which does not clear in seconds",
    )
    GEMINI_MAX_OUTPUT_TOKENS: int = Field(
        default=8192,
        description="Hard cap on Gemini output tokens (thinking included)",
    )
    GEMINI_THINKING_BUDGET: int = Field(
        default=0,
        description=(
            "Thinking tokens per call. 0 omits thinkingConfig entirely, which is "
            "the only value every registered Gemini model accepts."
        ),
    )
    GEMINI_THINKING_BUDGETS: str = Field(
        default="",
        description="Per-model override, e.g. 'gemini-3.8-flash:1024,gemini-3.5-flash:0'",
    )
    
    # Token Factory Sandbox
    SANDBOX_API_URL: str = Field(
        default="https://sandbox.api.nvidia.com/v1",
        description="Token Factory Sandbox API URL"
    )
    SANDBOX_API_KEY: str = Field(default="", description="Sandbox API key")
    SANDBOX_TIMEOUT: int = Field(default=300, description="Sandbox execution timeout in seconds")
    
    # Budget Profiles
    DEFAULT_BUDGET_PROFILE: str = Field(default="demo", description="Default budget profile name")
    
    # Worker
    WORKER_POOL_SIZE: int = Field(default=2, description="Number of worker processes")
    WORKER_LEASE_TTL: int = Field(default=300, description="Worker lease TTL in seconds")
    WORKER_POLL_INTERVAL: float = Field(default=1.0, description="Worker poll interval in seconds")
    
    # Audit
    AUDIT_HASH_ALGORITHM: str = Field(default="sha256", description="Hash algorithm for audit chain")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    
    # Frontend
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL for CORS")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
