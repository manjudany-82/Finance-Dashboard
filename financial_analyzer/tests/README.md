# AI Integration Tests (template & guidance)

This folder contains example and guidance for writing AI / LLM integration tests
that call Gemini (Google's generative API).

Key goals
- Keep CI deterministic and network-free when `GEMINI_API_KEY` is not present.
- Provide a clear example for local developers to run AI tests with a live key.

Markers & helpers
- `requires_gemini` / `ai_test` (registered in `financial_analyzer/conftest.py`):
  - Use either marker to mark tests that exercise the LLM layer.
  - When `GEMINI_API_KEY` is missing, these tests are automatically skipped with
    the reason: "Skipping AI integration test: GEMINI_API_KEY not set".

Recommended patterns
- Minimal skip-if decorator (inline):

```py
import os
import pytest

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Skipping AI integration test: GEMINI_API_KEY not set",
)
def test_llm_example():
    # call LLM layer safely and assert non-empty response
    pass
```

- Or import the `requires_gemini`/`ai_test` helper from module-level conftest and use it:

```py
from financial_analyzer.conftest import requires_gemini

@requires_gemini
def test_llm_template():
    ...
```

Local runs
- Run deterministic tests (AI tests skipped if no key):

```bash
pytest -q
```

- Run AI tests locally (set your key first):

```bash
export GEMINI_API_KEY="your_key_here"    # PowerShell: $env:GEMINI_API_KEY="..."
pytest -q
```

Notes
- Keep AI tests small and quota-friendly; assert only structure or presence of content,
  not exact model wording.
- The `test_ai_integration_example.py` file in this folder is a minimal template.
