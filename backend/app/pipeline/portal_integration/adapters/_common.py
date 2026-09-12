"""
Shared helpers for mock adapters — NOT a portal itself, imported by the others.

Centralizes the "pretend this is a slow, occasionally-flaky government portal"
behavior so every mock adapter demonstrates the same resilience story
(timeout/circuit-breaker per the architecture doc) with one implementation
instead of nine copies.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any


class SimulatedTimeout(Exception):
    """Raised internally when a mock adapter simulates a portal timeout.

    Adapters catch this themselves and convert it into an `UNAVAILABLE`
    `PortalVerificationResult` — it should never escape an adapter's
    `verify()` method.
    """


async def simulate_latency(min_ms: int = 150, max_ms: int = 600) -> None:
    """Sleep a random, realistic amount to stand in for a real HTTP round trip."""
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


def maybe_fail(failure_rate: float) -> None:
    """Randomly raise SimulatedTimeout to exercise the unavailable/circuit-breaker path.

    `failure_rate` is 0.0 by default in every adapter (deterministic demo runs);
    pass e.g. 0.15 in tests or a "chaos mode" toggle to prove the orchestrator
    tolerates a portal going down mid-run without blocking the rest.
    """
    if failure_rate > 0 and random.random() < failure_rate:
        raise SimulatedTimeout("simulated portal timeout")


def normalize(value: str | None) -> str:
    """Loose normalization for comparing bidder-submitted vs. mock-portal names/ids."""
    return (value or "").strip().upper()


NAME_MISMATCH_SUFFIX = " (NAME ON FILE DIFFERS)"


def fields_with_confidence(base_confidence: float, jitter: float = 0.03) -> float:
    """Small deterministic-ish jitter so confidence scores don't look hardcoded."""
    return round(min(0.99, max(0.5, base_confidence + random.uniform(-jitter, jitter))), 2)
