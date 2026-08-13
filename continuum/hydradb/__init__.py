"""Thin Continuum integration layer for HydraDB."""

from .client import HydraDBClient, QueryResult
from .config import HydraDBConfig

__all__ = ["HydraDBClient", "HydraDBConfig", "QueryResult"]

