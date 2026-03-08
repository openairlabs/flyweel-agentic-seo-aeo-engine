#!/usr/bin/env python3
"""
Test configuration and fixtures
Provides shared utilities for all tests
"""
import pytest
import os


def has_api_keys() -> bool:
    """Check if required API keys are available"""
    required_keys = ['GOOGLE_API_KEY', 'PERPLEXITY_API_KEY', 'NEBIUS_API_KEY']
    return all(os.getenv(key) for key in required_keys)


def skip_if_no_api_keys(func):
    """Decorator to skip tests if API keys are missing"""
    return pytest.mark.skipif(
        not has_api_keys(),
        reason="API keys not available (GOOGLE_API_KEY, PERPLEXITY_API_KEY, NEBIUS_API_KEY required)"
    )(func)


@pytest.fixture
def api_keys_available():
    """Fixture to check API key availability"""
    return has_api_keys()


@pytest.fixture
def require_api_keys():
    """Fixture that skips test if API keys are missing"""
    if not has_api_keys():
        pytest.skip("API keys not available - skipping integration test")
