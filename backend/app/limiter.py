"""backend/app/limiter.py
─────────────────────────────────────────────────────────────
Global rate-limiter instance shared across all route modules.

The limiter uses the client's remote IP address as the rate-key.
Individual endpoint limits are declared via ``@limiter.limit(...)``
decorators in each route file.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

__all__ = ["limiter"]
