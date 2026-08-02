"""
backend/rate_limit.py

Shared `slowapi` Limiter instance — lives in its own module (not
backend/main.py) so routers can import and apply it without a circular
import (main.py imports routers; routers would otherwise need to import
the limiter back from main.py).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
