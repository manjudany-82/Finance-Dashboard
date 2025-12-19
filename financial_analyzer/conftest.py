import os
import pytest


# conftest.py: test configuration for AI integration gating
#
# This file registers markers for AI/LLM tests and ensures any test marked
# with `requires_gemini` or `ai_test` is automatically skipped when the
# `GEMINI_API_KEY` environment variable is not present. This prevents CI
# failures in environments where secrets are intentionally not configured.


# Register custom markers for AI/Gemini integration tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_gemini: mark test as requiring GEMINI_API_KEY (will be skipped if not set)"
    )
    config.addinivalue_line(
        "markers",
        "ai_test: alias for requires_gemini; marks tests that exercise LLM/Gemini integration"
    )


# Detect whether GEMINI API key is available in the environment at collection time
GEMINI_MISSING = not bool(os.getenv("GEMINI_API_KEY"))


# Convenience decorator users can import directly from tests: @requires_gemini
requires_gemini = pytest.mark.skipif(
    GEMINI_MISSING,
    reason="Skipping AI integration test: GEMINI_API_KEY not set",
)

# Alias for symmetry
ai_test = requires_gemini


def pytest_collection_modifyitems(config, items):
    """Automatically skip any collected tests marked as AI/Gemini integration when
    `GEMINI_API_KEY` is not present. This ensures CI remains deterministic and
    network-free unless the secret is explicitly provided.
    """
    if GEMINI_MISSING:
        skip_marker = pytest.mark.skip(reason="Skipping AI integration test: GEMINI_API_KEY not set")
        for item in items:
            # Skip tests marked either with @pytest.mark.requires_gemini or @pytest.mark.ai_test
            if item.get_closest_marker("requires_gemini") or item.get_closest_marker("ai_test"):
                item.add_marker(skip_marker)
