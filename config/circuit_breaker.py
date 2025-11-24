"""
Circuit breaker implementation for external service calls.
Prevents cascading failures by stopping requests to failing services.
"""
import time
import logging
from enum import Enum
from typing import Callable, Optional, Any
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Open circuit after N failures
    success_threshold: int = 2  # Close circuit after N successes in half-open
    timeout: float = 60.0  # Time to wait before trying half-open (seconds)
    expected_exception: type = Exception  # Exception type to catch


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    recent_results: deque = field(default_factory=lambda: deque(maxlen=100))


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Usage:
        breaker = CircuitBreaker("external_api")

        @breaker
        def call_external_api():
            # Make API call
            pass
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = False  # Simple lock for thread safety (could use threading.Lock)

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""

        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        self.stats.total_requests += 1

        # Check circuit state
        if self.stats.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.stats.state = CircuitState.HALF_OPEN
                self.stats.successes = 0
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN. "
                    f"Last failure: {self.stats.last_failure_time}"
                )

        # Attempt the call
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.stats.last_failure_time is None:
            return True

        elapsed = time.time() - self.stats.last_failure_time
        return elapsed >= self.config.timeout

    def _on_success(self):
        """Handle successful call."""
        self.stats.recent_results.append(("success", time.time()))
        self.stats.total_successes += 1

        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.successes += 1
            if self.stats.successes >= self.config.success_threshold:
                self._close_circuit()
        elif self.stats.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.stats.failures = 0

    def _on_failure(self):
        """Handle failed call."""
        self.stats.recent_results.append(("failure", time.time()))
        self.stats.total_failures += 1
        self.stats.failures += 1
        self.stats.last_failure_time = time.time()

        if self.stats.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            self.stats.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker {self.name} failed in HALF_OPEN, returning to OPEN"
            )
        elif self.stats.state == CircuitState.CLOSED:
            if self.stats.failures >= self.config.failure_threshold:
                self._open_circuit()

    def _open_circuit(self):
        """Open the circuit breaker."""
        self.stats.state = CircuitState.OPEN
        logger.error(
            f"Circuit breaker {self.name} OPENED after {self.stats.failures} failures. "
            f"Will retry after {self.config.timeout}s"
        )

    def _close_circuit(self):
        """Close the circuit breaker."""
        self.stats.state = CircuitState.CLOSED
        self.stats.failures = 0
        self.stats.successes = 0
        logger.info(f"Circuit breaker {self.name} CLOSED (recovered)")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failures": self.stats.failures,
            "successes": self.stats.successes,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "failure_rate": (
                self.stats.total_failures / self.stats.total_requests
                if self.stats.total_requests > 0
                else 0
            ),
            "last_failure_time": (
                self.stats.last_failure_time if self.stats.last_failure_time else None
            ),
        }

    def reset(self):
        """Manually reset the circuit breaker."""
        self.stats.state = CircuitState.CLOSED
        self.stats.failures = 0
        self.stats.successes = 0
        logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


# Global circuit breakers registry
_circuit_breakers = {}


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker.

    Args:
        name: Circuit breaker name
        config: Configuration (optional)

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict:
    """Get statistics for all circuit breakers."""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}
