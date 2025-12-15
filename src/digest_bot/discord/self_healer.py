#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Self-Healing System
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Self-healing capabilities for the Discord bot.

Features:
- Automatic reconnection with exponential backoff
- Health monitoring and status reporting
- Error recovery and graceful degradation
- Circuit breaker pattern for external services
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH STATUS
# ══════════════════════════════════════════════════════════════════════════════


class HealthState(Enum):
    """Health states for the bot."""

    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    RECOVERING = auto()
    CRITICAL = auto()


@dataclass
class HealthStatus:
    """
    Current health status of the bot.

    Tracks various health metrics and provides
    overall health assessment.
    """

    state: HealthState = HealthState.HEALTHY
    last_heartbeat: datetime = field(default_factory=datetime.now)
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    consecutive_errors: int = 0
    total_errors: int = 0
    uptime_start: datetime = field(default_factory=datetime.now)
    reconnect_count: int = 0
    components: Dict[str, HealthState] = field(default_factory=dict)

    @property
    def uptime(self) -> timedelta:
        """Get current uptime."""
        return datetime.now() - self.uptime_start

    @property
    def uptime_str(self) -> str:
        """Get uptime as human-readable string."""
        delta = self.uptime
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)

    def record_heartbeat(self) -> None:
        """Record successful heartbeat."""
        self.last_heartbeat = datetime.now()
        if self.consecutive_errors > 0:
            logger.info(f"Recovered after {self.consecutive_errors} consecutive errors")
        self.consecutive_errors = 0
        self._update_state()

    def record_error(self, error: str) -> None:
        """Record an error occurrence."""
        self.last_error = error
        self.last_error_time = datetime.now()
        self.consecutive_errors += 1
        self.total_errors += 1
        self._update_state()
        logger.warning(f"Error recorded ({self.consecutive_errors} consecutive): {error}")

    def record_reconnect(self) -> None:
        """Record a reconnection attempt."""
        self.reconnect_count += 1
        logger.info(f"Reconnection #{self.reconnect_count}")

    def set_component_health(self, component: str, state: HealthState) -> None:
        """Set health state for a specific component."""
        self.components[component] = state
        self._update_state()

    def _update_state(self) -> None:
        """Update overall health state based on metrics."""
        # Check component health
        unhealthy_components = sum(
            1 for s in self.components.values() if s in (HealthState.UNHEALTHY, HealthState.CRITICAL)
        )

        if self.consecutive_errors >= 10 or unhealthy_components >= 2:
            self.state = HealthState.CRITICAL
        elif self.consecutive_errors >= 5 or unhealthy_components >= 1:
            self.state = HealthState.UNHEALTHY
        elif self.consecutive_errors >= 2:
            self.state = HealthState.DEGRADED
        elif self.consecutive_errors > 0:
            self.state = HealthState.RECOVERING
        else:
            self.state = HealthState.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "state": self.state.name,
            "uptime": self.uptime_str,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "last_error": self.last_error,
            "consecutive_errors": self.consecutive_errors,
            "total_errors": self.total_errors,
            "reconnect_count": self.reconnect_count,
            "components": {k: v.name for k, v in self.components.items()},
        }


# ══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════════════════


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = auto()  # Normal operation
    OPEN = auto()  # Failing, reject requests
    HALF_OPEN = auto()  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Prevents cascading failures by stopping calls
    to failing services.
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0

    def can_execute(self) -> bool:
        """Check if circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if self.last_failure_time is None:
                return True

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(f"Circuit {self.name}: transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self) -> None:
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                logger.info(f"Circuit {self.name}: recovered, transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failures = 0
        else:
            self.failures = max(0, self.failures - 1)

    def record_failure(self) -> None:
        """Record failed call."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name}: failure in HALF_OPEN, reopening")
            self.state = CircuitState.OPEN
        elif self.failures >= self.failure_threshold:
            logger.warning(f"Circuit {self.name}: threshold reached, opening circuit")
            self.state = CircuitState.OPEN


# ══════════════════════════════════════════════════════════════════════════════
# SELF HEALER
# ══════════════════════════════════════════════════════════════════════════════


class SelfHealer:
    """
    Self-healing manager for the Discord bot.

    Provides:
    - Automatic reconnection with exponential backoff
    - Health monitoring
    - Error recovery strategies
    - Circuit breakers for external services
    """

    # Backoff configuration
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 300.0  # 5 minutes
    BACKOFF_MULTIPLIER = 2.0
    JITTER_FACTOR = 0.1

    def __init__(self):
        self.health = HealthStatus()
        self._current_backoff = self.INITIAL_BACKOFF
        self._shutdown_event = asyncio.Event()
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._recovery_callbacks: List[Callable] = []
        self._heartbeat_task: Optional[asyncio.Task] = None

    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    def register_recovery_callback(self, callback: Callable) -> None:
        """Register a callback for recovery events."""
        self._recovery_callbacks.append(callback)

    async def _notify_recovery(self) -> None:
        """Notify all recovery callbacks."""
        for callback in self._recovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")

    def calculate_backoff(self) -> float:
        """
        Calculate next backoff duration with jitter.

        Uses exponential backoff with jitter to prevent
        thundering herd problems.
        """
        import random

        # Add jitter
        jitter = random.uniform(-self.JITTER_FACTOR, self.JITTER_FACTOR)
        backoff = self._current_backoff * (1 + jitter)

        # Increase for next time
        self._current_backoff = min(self._current_backoff * self.BACKOFF_MULTIPLIER, self.MAX_BACKOFF)

        return backoff

    def reset_backoff(self) -> None:
        """Reset backoff to initial value after successful connection."""
        self._current_backoff = self.INITIAL_BACKOFF

    async def wait_before_reconnect(self) -> float:
        """
        Wait before attempting reconnection.

        Returns:
            Actual wait time in seconds
        """
        wait_time = self.calculate_backoff()
        logger.info(f"Waiting {wait_time:.1f}s before reconnect attempt...")

        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=wait_time)
            # Shutdown was requested
            return 0
        except asyncio.TimeoutError:
            # Normal timeout, proceed with reconnect
            return wait_time

    async def reconnect_loop(
        self,
        connect_func: Callable,
        max_attempts: int = 0,  # 0 = infinite
    ) -> bool:
        """
        Attempt reconnection with exponential backoff.

        Args:
            connect_func: Async function to establish connection
            max_attempts: Max reconnection attempts (0 = infinite)

        Returns:
            True if connected, False if gave up
        """
        attempts = 0

        while not self._shutdown_event.is_set():
            attempts += 1
            self.health.record_reconnect()

            if max_attempts > 0 and attempts > max_attempts:
                logger.error(f"Max reconnection attempts ({max_attempts}) exceeded")
                return False

            try:
                logger.info(f"Reconnection attempt #{attempts}")
                await connect_func()

                # Success!
                self.reset_backoff()
                self.health.record_heartbeat()
                await self._notify_recovery()
                logger.info("Successfully reconnected!")
                return True

            except Exception as e:
                self.health.record_error(str(e))
                logger.warning(f"Reconnection failed: {e}")

                if await self.wait_before_reconnect() == 0:
                    return False  # Shutdown requested

        return False

    async def start_heartbeat(
        self,
        interval: float = 30.0,
        check_func: Optional[Callable] = None,
    ) -> None:
        """
        Start heartbeat monitoring.

        Args:
            interval: Seconds between heartbeats
            check_func: Optional async function to check health
        """

        async def heartbeat_loop():
            while not self._shutdown_event.is_set():
                try:
                    if check_func:
                        if asyncio.iscoroutinefunction(check_func):
                            await check_func()
                        else:
                            check_func()

                    self.health.record_heartbeat()

                except Exception as e:
                    self.health.record_error(str(e))

                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Normal timeout

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    def is_shutting_down(self) -> bool:
        """Check if shutdown was requested."""
        return self._shutdown_event.is_set()

    def with_circuit_breaker(self, circuit_name: str):
        """
        Decorator to wrap a function with circuit breaker.

        Usage:
            @healer.with_circuit_breaker("llm")
            async def call_llm():
                ...
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                circuit = self.get_circuit(circuit_name)

                if not circuit.can_execute():
                    raise RuntimeError(f"Circuit {circuit_name} is open")

                try:
                    result = await func(*args, **kwargs)
                    circuit.record_success()
                    return result
                except Exception:
                    circuit.record_failure()
                    raise

            return wrapper

        return decorator

    def with_retry(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        exceptions: tuple = (Exception,),
    ):
        """
        Decorator to add retry logic to a function.

        Usage:
            @healer.with_retry(max_retries=3)
            async def flaky_operation():
                ...
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_error = None

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        if attempt < max_retries:
                            wait = delay * (2**attempt)
                            logger.warning(f"Retry {attempt + 1}/{max_retries} " f"after {wait:.1f}s: {e}")
                            await asyncio.sleep(wait)

                raise last_error

            return wrapper

        return decorator
