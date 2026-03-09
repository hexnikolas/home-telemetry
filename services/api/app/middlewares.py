"""
FastAPI middleware for request logging and correlation IDs.

Provides:
- Automatic correlation ID generation/extraction
- Request/response logging
- Performance metrics
- Context binding for downstream operations
"""

import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from shared.logging_config import set_correlation_id, set_request_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts or generates correlation IDs for request tracing.
    
    - Extracts from X-Correlation-ID header if present
    - Generates new UUID if not present
    - Adds to response headers
    - Makes available in context for all downstream operations
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract correlation ID from headers or generate new one
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4())
        )
        
        # Extract or generate request ID
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4())
        )
        
        # Set in context for logging
        set_correlation_id(correlation_id)
        set_request_id(request_id)
        
        # Call the next middleware/route
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests and responses.
    
    Logs:
    - Request method, path, query params
    - Response status code
    - Processing time
    - Request/response sizes
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        from shared.logging_config import logger
        
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "unknown")
        
        # Log request
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "client": request.client.host if request.client else "unknown",
            }
        )
        
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                f"✗ {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                },
            )
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            f"← {response.status_code} {request.method} {request.url.path} ({duration_ms:.2f}ms)",
            extra={
                "status_code": response.status_code,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            }
        )
        
        return response
