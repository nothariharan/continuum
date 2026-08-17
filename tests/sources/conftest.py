"""Shared fixtures for source tests. HydraDB required only where requested."""

from __future__ import annotations

import pytest

from continuum.hydradb import HydraDBClient


@pytest.fixture
def client():
    with HydraDBClient() as value:
        yield value