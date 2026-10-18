"""Shared pytest fixtures. pytest loads this file automatically."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def empty_cache() -> None:
    """Every test starts with an empty cache, so results never leak between tests."""
    cache.clear()
