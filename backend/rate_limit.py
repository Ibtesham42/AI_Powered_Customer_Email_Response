"""Shared rate limiter (slowapi).

Uses in-memory storage — fine for a single instance. A multi-instance
deployment (e.g. Cloud Run) must point this at Redis via a storage URI.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
