"""Example AI integration test template.

This test demonstrates the recommended pattern for LLM/Gemini integration tests.
It is intentionally minimal and marked to skip when `GEMINI_API_KEY` is not set.

Usage:
- Run full AI tests locally by exporting `GEMINI_API_KEY`.
- In CI, the test will be skipped unless the secret is provided.
"""
import os
import pytest

from financial_analyzer.llm_insights import AIAnalyst


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Skipping AI integration test: GEMINI_API_KEY not set"
)
def test_gemini_smoke_response():
    """Simple smoke test that calls the AI layer and asserts a non-empty response.

    This test does NOT assert on exact wording or model output. It only ensures the
    AI layer returns a non-empty, well-formed response when a key is available.
    """
    ai = AIAnalyst(preferred_model=os.getenv("GEMINI_PREFERRED_MODEL", "gemini-2.0-flash"))

    # Minimal payload — keep this small to limit quota usage
    payload = {"ytd_sales": 1000, "mom_sales_pct": 2}

    resp = ai.get_insights("Overview", payload)

    # Basic structural assertions
    assert resp is not None
    assert isinstance(resp, dict)

    bullets = resp.get("bullets") if isinstance(resp, dict) else None
    assert bullets is not None

    # Ensure at least one non-empty bullet returned
    non_empty = [b for b in bullets if isinstance(b, str) and b.strip()]
    assert len(non_empty) > 0
