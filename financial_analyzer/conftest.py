import os
import pytest


# Register custom marker for AI/Gemini integration tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_gemini: mark test as requiring GEMINI_API_KEY (will be skipped if not set)"
    )


# Automatically skip tests marked with @pytest.mark.requires_gemini when GEMINI_API_KEY missing
GEMINI_MISSING = not bool(os.getenv("GEMINI_API_KEY"))

# Convenience decorator users can import: @requires_gemini
requires_gemini = pytest.mark.skipif(
    not bool(os.getenv("GEMINI_API_KEY")),
    reason="Skipping AI integration test: GEMINI_API_KEY not set"
)


def pytest_collection_modifyitems(config, items):
    if GEMINI_MISSING:
        skip_marker = pytest.mark.skip(reason="Skipping AI integration test: GEMINI_API_KEY not set")
        for item in items:
            if item.get_closest_marker("requires_gemini"):
                item.add_marker(skip_marker)
