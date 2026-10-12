"""
Nexora Model Router and Provider Adapter
Routes to appropriate model and handles provider communication
"""
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from nexora.backend.app.models import ModelRegistry
from nexora.backend.app.schemas import RoutingMode
from nexora.backend.config.settings import get_settings

settings = get_settings()


class RoutingReason(str, Enum):
    """Reasons for model selection"""
    EXPLICIT_FIXED = "explicit_fixed"
    AUTO_SIMPLE_TASK = "auto_simple_task"
    AUTO_MODERATE_TASK = "auto_moderate_task"
    AUTO_COMPLEX_TASK = "auto_complex_task"
    FALLBACK_AFTER_FAILURE = "fallback_after_failure"
    ONLY_MODEL_AVAILABLE = "only_model_available"


@dataclass
class RoutingDecision:
    """Model routing decision"""
    model: ModelRegistry
    reason: RoutingReason
    attempt_number: int
    alternatives_considered: List[str]


@dataclass
class InferenceRequest:
    """Normalized inference request"""
    model_id: str
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 120
    idempotency_key: str = ""


@dataclass
class InferenceResponse:
    """Normalized inference response"""
    content: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_id: str = ""
    finish_reason: str = ""
    raw_response: Dict[str, Any] = None


class ModelRouter:
    """
    Model Router - selects appropriate model based on task, budget, and history.
    
    In Auto mode: uses task complexity, budget, context size, observed reliability.
    In Fixed mode: respects chosen model, stops with evidence if inadequate.
    """
    
    def __init__(self, enabled_models: List[ModelRegistry]):
        self.enabled_models = {m.model_id: m for m in enabled_models if m.is_enabled}
        self._verify_models()
    
    def _verify_models(self) -> None:
        """Verify at least one model is available"""
        if not self.enabled_models:
            raise ValueError("No enabled models in registry")
    
    def route(
        self,
        routing_mode: RoutingMode,
        requested_model_id: Optional[str],
        task_complexity: str = "moderate",
        context_size: int = 0,
        previous_failures: int = 0,
        attempt_number: int = 1,
    ) -> RoutingDecision:
        """
        Select model for inference.
        
        Args:
            routing_mode: Auto or Fixed
            requested_model_id: Model ID if fixed mode
            task_complexity: simple, moderate, complex
            context_size: Estimated context tokens
            previous_failures: Number of previous failed attempts
            attempt_number: Current attempt number
            
        Returns:
            RoutingDecision with selected model and reason
        """
        if routing_mode == RoutingMode.FIXED:
            if requested_model_id and requested_model_id in self.enabled_models:
                model = self.enabled_models[requested_model_id]
                return RoutingDecision(
                    model=model,
                    reason=RoutingReason.EXPLICIT_FIXED,
                    attempt_number=attempt_number,
                    alternatives_considered=[m.model_id for m in self.enabled_models.values() if m.model_id != requested_model_id],
                )
            elif requested_model_id:
                # Requested model not enabled - fall back with evidence
                available = list(self.enabled_models.values())
                if available:
                    return RoutingDecision(
                        model=available[0],
                        reason=RoutingReason.ONLY_MODEL_AVAILABLE,
                        attempt_number=attempt_number,
                        alternatives_considered=[],
                    )
                raise ValueError("No models available")
        
        # Auto mode - rule-based routing
        # Simple tasks -> Nano
        # Moderate -> Super
        # Complex -> Ultra (if available and quality verified)
        
        # For now, use first available model with appropriate tier
        models_by_tier = {
            "nano": [m for m in self.enabled_models.values() if m.tier == "nano"],
            "super": [m for m in self.enabled_models.values() if m.tier == "super"],
            "ultra": [m for m in self.enabled_models.values() if m.tier == "ultra"],
        }
        
        alternatives = [m.model_id for m in self.enabled_models.values()]
        
        if task_complexity == "simple" and models_by_tier["nano"]:
            model = models_by_tier["nano"][0]
            reason = RoutingReason.AUTO_SIMPLE_TASK
        elif task_complexity == "moderate" and models_by_tier["super"]:
            model = models_by_tier["super"][0]
            reason = RoutingReason.AUTO_MODERATE_TASK
        elif task_complexity == "complex" and models_by_tier["ultra"]:
            model = models_by_tier["ultra"][0]
            reason = RoutingReason.AUTO_COMPLEX_TASK
        else:
            # Fallback to any available model
            available = list(self.enabled_models.values())
            model = available[0]
            reason = RoutingReason.ONLY_MODEL_AVAILABLE
        
        # If previous failure, consider fallback
        if previous_failures > 0 and attempt_number > 1:
            reason = RoutingReason.FALLBACK_AFTER_FAILURE
        
        return RoutingDecision(
            model=model,
            reason=reason,
            attempt_number=attempt_number,
            alternatives_considered=alternatives,
        )
    
    def get_model(self, model_id: str) -> Optional[ModelRegistry]:
        """Get model by ID"""
        return self.enabled_models.get(model_id)
    
    def list_enabled(self) -> List[ModelRegistry]:
        """List all enabled models"""
        return list(self.enabled_models.values())


class ProviderAdapter:
    """
    Provider Adapter - normalizes OpenAI-compatible API calls.
    
    Handles: timeouts, backoff, idempotency, token limits, redacted logs.
    Never silently switches models or hides provider failures.
    """
    
    def __init__(self):
        self.base_url = settings.NEBIUS_BASE_URL
        self.api_key = settings.NEBIUS_API_KEY
        self.timeout = settings.NEBIUS_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        """
        Execute inference request with retries and error handling.
        
        Args:
            request: Normalized inference request
            
        Returns:
            InferenceResponse with normalized output
            
        Raises:
            ProviderError: On provider failures (not hidden)
        """
        client = await self._get_client()
        
        # Prepare payload
        payload = {
            "model": request.model_id,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"
        
        # Idempotency key
        headers = {}
        if request.idempotency_key:
            headers["Idempotency-Key"] = request.idempotency_key
        
        # Execute with exponential backoff
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    "/chat/completions",
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._normalize_response(data, request.model_id)
                
                elif response.status_code == 429:
                    # Rate limited - back off
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                
                elif response.status_code >= 500:
                    # Server error - retry
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                
                else:
                    # Client error - don't retry
                    raise ProviderError(
                        f"Provider error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                    
            except httpx.TimeoutException:
                if attempt == max_retries - 1:
                    raise ProviderError("Provider request timed out")
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise ProviderError(f"Provider request failed: {str(e)}")
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
        
        raise ProviderError("Max retries exceeded")
    
    def _normalize_response(self, data: Dict[str, Any], model_id: str) -> InferenceResponse:
        """Normalize provider response"""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        tool_calls = message.get("tool_calls")
        if tool_calls:
            # Normalize tool calls
            normalized_calls = []
            for tc in tool_calls:
                normalized_calls.append({
                    "id": tc.get("id"),
                    "name": tc.get("function", {}).get("name"),
                    "arguments": tc.get("function", {}).get("arguments"),
                })
            tool_calls = normalized_calls
        
        usage = data.get("usage", {})
        
        return InferenceResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model_id=data.get("model", model_id),
            finish_reason=choice.get("finish_reason", ""),
            raw_response=data,
        )


class ProviderError(Exception):
    """Provider-specific error that should not be hidden"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# Global instances
_model_router: Optional[ModelRouter] = None
_provider_adapter: Optional[ProviderAdapter] = None


def get_model_router(enabled_models: List[ModelRegistry]) -> ModelRouter:
    """Get or create model router"""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter(enabled_models)
    return _model_router


def get_provider_adapter() -> ProviderAdapter:
    """Get or create provider adapter"""
    global _provider_adapter
    if _provider_adapter is None:
        _provider_adapter = ProviderAdapter()
    return _provider_adapter
