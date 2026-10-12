import pytest
import tempfile
from pathlib import Path
from nexora.backend.app.core.context import skeletonize_python, ContextOptimizer
from nexora.backend.app.models import ModelRegistry
from nexora.backend.app.worker.orchestrator import (
    calculate_dynamic_output_budget,
    extract_clean_code,
)


def test_skeletonize_python_preserves_signatures_and_docstrings():
    sample_code = '''
import os
from typing import List, Optional

class DataStore:
    """Store data in memory."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.items = []

    def get_items(self) -> List[str]:
        """Return all items."""
        return [str(x) for x in self.items]

def process_data(store: DataStore, flag: bool = True) -> Optional[int]:
    """Process data function."""
    if not flag:
        return None
    return len(store.items)
'''
    skeleton = skeletonize_python(sample_code)
    
    # Signatures, imports, and docstrings must be present
    assert "import os" in skeleton
    assert "class DataStore:" in skeleton
    assert '"""Store data in memory."""' in skeleton
    assert "def __init__(self, capacity: int=100):" in skeleton or "def __init__(self, capacity: int = 100):" in skeleton
    assert "def get_items(self) -> List[str]:" in skeleton
    assert '"""Return all items."""' in skeleton
    assert "def process_data(store: DataStore, flag: bool=True) -> Optional[int]:" in skeleton or "def process_data(store: DataStore, flag: bool = True) -> Optional[int]:" in skeleton
    assert '"""Process data function."""' in skeleton
    
    # Internal bodies must be replaced
    assert "self.capacity = capacity" not in skeleton
    assert "return [str(x) for x in self.items]" not in skeleton
    assert "return len(store.items)" not in skeleton


def test_skeletonize_fallback_on_invalid_syntax():
    invalid_code = "def invalid_func(::: broken syntax"
    # Should safely return source code without crashing
    assert skeletonize_python(invalid_code) == invalid_code


def test_context_optimizer_safeguard_and_caching():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target_file = root / "calculator.py"
        target_file.write_text("""
class Calculator:
    \"\"\"Calculator class.\"\"\"
    def add(self, a: int, b: int) -> int:
        return a + b
""", encoding="utf-8")

        ref_file = root / "utils.py"
        ref_file.write_text("""
import math

def helper_function(val: float) -> float:
    \"\"\"Helper calculation.\"\"\"
    intermediate = math.sqrt(val) * 2.5
    return intermediate + 42.0
""", encoding="utf-8")

        optimizer = ContextOptimizer(str(root))
        model = ModelRegistry(
            model_id="test-model",
            display_name="Test",
            context_capacity=8192,
            max_output_tokens=1024,
        )

        # Query targeting calculator specifically
        pkg1 = optimizer.build_context(
            task_query="Fix addition bug in calculator.py",
            model=model,
        )

        included_map = {f["path"]: f for f in pkg1.included_files}
        
        # Calculator was targeted -> must have full content
        if "calculator.py" in included_map:
            assert included_map["calculator.py"]["content_mode"] == "full"
            assert "return a + b" in included_map["calculator.py"]["content"]

        # Run 2 on same query -> should hit cache
        pkg2 = optimizer.build_context(
            task_query="Fix addition bug in calculator.py",
            model=model,
        )
        assert pkg2.cache_hits >= 1


def test_skeletonize_preserves_decorators_and_async():
    sample = '''
from dataclasses import dataclass

@dataclass
class ServiceConfig:
    timeout: int = 30
    retry_count: int = 3

    @property
    def is_valid(self) -> bool:
        """Validate config values."""
        return self.timeout > 0 and self.retry_count >= 0

    @classmethod
    async def fetch_async(cls, endpoint: str) -> "ServiceConfig":
        """Asynchronously load config."""
        res = await some_http_client(endpoint)
        return cls(timeout=res.timeout)
'''
    skeleton = skeletonize_python(sample)

    # Decorators must be preserved
    assert "@dataclass" in skeleton
    assert "@property" in skeleton
    assert "@classmethod" in skeleton

    # Async keyword and signature preserved
    assert "async def fetch_async(cls, endpoint: str) -> 'ServiceConfig':" in skeleton or "async def fetch_async(cls, endpoint: str) -> \"ServiceConfig\":" in skeleton
    assert '"""Asynchronously load config."""' in skeleton

    # Class attributes preserved
    assert "timeout: int = 30" in skeleton
    assert "retry_count: int = 3" in skeleton

    # Body implementation replaced with pass
    assert "return self.timeout > 0" not in skeleton
    assert "res = await some_http_client" not in skeleton


def test_dynamic_token_budget_calculation():
    # Simple DSA or short utility query (< 12 words without fix/add/test/implement) -> 512
    assert calculate_dynamic_output_budget("Two sum in Python", ceiling=2000) == 512
    assert calculate_dynamic_output_budget("Binary search algorithm", ceiling=2000) == 512

    # Standard feature / fix / test / implement -> 1024
    assert calculate_dynamic_output_budget("Fix the user authentication token validation logic", ceiling=2000) == 1024
    assert calculate_dynamic_output_budget("Add unit tests for payment webhook processing", ceiling=2000) == 1024
    assert calculate_dynamic_output_budget("Implement a custom LRU cache class", ceiling=2000) == 1024

    # Complex refactor / architecture -> 1536
    assert calculate_dynamic_output_budget("Refactor the multi-tenant architecture and system data model", ceiling=2000) == 1536

    # Clamping against ceiling
    assert calculate_dynamic_output_budget("Refactor database layer", ceiling=500) == 500
    assert calculate_dynamic_output_budget("Two sum in Python", ceiling=256) == 256


def test_extract_clean_code_preserves_docstrings_with_backticks():
    # Code with a markdown example inside its docstring
    raw_code = '''def markdown_parser(text: str) -> str:
    """
    Parse markdown snippet.

    Example:
    ```
    parsed = parser("# Header")
    ```

    Returns the formatted text.
    """
    return text.strip()'''
    # When text does not start with an outer markdown fence, extract_clean_code preserves it verbatim
    extracted = extract_clean_code(raw_code)
    assert extracted == raw_code
    assert "```\n    parsed = parser" in extracted
    assert 'Returns the formatted text.' in extracted


def test_extract_clean_code_strips_outer_fence_and_trailing_explanation():
    model_output = '''```python
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

### Explanation
This function performs addition of two integers.
'''
    cleaned = extract_clean_code(model_output)
    assert "def add(a: int, b: int) -> int:" in cleaned
    assert "return a + b" in cleaned
    assert "```" not in cleaned
    assert "### Explanation" not in cleaned
    assert "This function performs addition" not in cleaned

