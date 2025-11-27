"""
Circuit Breaker middleware for FastAPI.
Prevents cascading failures by monitoring error rates and opening the circuit when threshold is exceeded.
"""
import time
from enum import Enum
from typing import Callable, Dict, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.core.logging import logger


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is open, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker implementation for monitoring service health.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        excluded_paths: Optional[list] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes needed to close circuit from half-open
            timeout: Time in seconds before attempting to close circuit
            excluded_paths: List of paths to exclude from circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/openapi.json", "/redoc"]
        
        # Circuit state tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.metrics: Dict[str, int] = {
            "total_requests": 0,
            "failed_requests": 0,
            "rejected_requests": 0
        }
    
    def should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from circuit breaker"""
        return any(excluded in path for excluded in self.excluded_paths)
    
    def call(self, request: Request) -> Optional[JSONResponse]:
        """
        Check if request should be allowed based on circuit state.
        
        Returns:
            JSONResponse if request should be rejected, None otherwise
        """
        if self.should_exclude_path(request.url.path):
            return None
        
        self.metrics["total_requests"] += 1
        
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                logger.info("Circuit breaker transitioning from OPEN to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                self.metrics["rejected_requests"] += 1
                logger.warning(f"Circuit breaker is OPEN, rejecting request to {request.url.path}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service temporarily unavailable",
                        "message": "Circuit breaker is open. Service is experiencing issues.",
                        "retry_after": int(self.timeout - (time.time() - (self.last_failure_time or 0)))
                    }
                )
        
        return None
    
    def on_success(self):
        """Handle successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(f"Circuit breaker success count: {self.success_count}/{self.success_threshold}")
            
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker transitioning from HALF_OPEN to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def on_failure(self):
        """Handle failed request"""
        self.metrics["failed_requests"] += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker failure in HALF_OPEN state, reopening circuit")
            self.state = CircuitState.OPEN
            self.success_count = 0
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.debug(f"Circuit breaker failure count: {self.failure_count}/{self.failure_threshold}")
            
            if self.failure_count >= self.failure_threshold:
                logger.error("Circuit breaker failure threshold exceeded, opening circuit")
                self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Get current circuit breaker state and metrics"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "metrics": self.metrics,
            "last_failure_time": self.last_failure_time
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60
)


async def circuit_breaker_middleware(request: Request, call_next: Callable) -> Response:
    """
    FastAPI middleware for circuit breaker.
    """
    # Check if request should be rejected
    rejection_response = circuit_breaker.call(request)
    if rejection_response:
        return rejection_response
    
    try:
        response = await call_next(request)
        
        # Only track server errors (5xx) as failures
        if response.status_code >= 500:
            circuit_breaker.on_failure()
        else:
            circuit_breaker.on_success()
        
        return response
    
    except Exception as e:
        logger.error(f"Unhandled exception in circuit breaker: {str(e)}")
        circuit_breaker.on_failure()
        raise