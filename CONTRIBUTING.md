# Contributing to Nadlan-MCP

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/nadlan-mcp.git
cd nadlan-mcp
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 4. Verify Setup

```bash
# Run tests
pytest tests/ -m "not api_health" -q

# Check code quality
ruff check .
ruff format --check .
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

Follow the code style guidelines below.

### 3. Run Tests

```bash
# Run fast tests
pytest tests/ -m "not api_health" -q

# Run with coverage
pytest tests/ -m "not api_health" --cov=nadlan_mcp

# Run specific test file
pytest tests/govmap/test_filters.py -v
```

### 4. Code Quality Checks

```bash
# Format code
ruff format .

# Lint code
ruff check . --fix

# Check remaining issues
ruff check .
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve issue with..."
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `chore:` - Build/tooling changes

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python Style Guide

We use **Ruff** for formatting and linting (replaces black, isort, flake8):

- Line length: 100 characters
- Use double quotes for strings
- Follow PEP 8 conventions

### Formatting

```bash
# Auto-format all code
ruff format .
```

### Linting

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Optional
from nadlan_mcp.govmap.models import Deal

def process_deals(
    deals: List[Deal],
    min_price: Optional[float] = None
) -> List[Deal]:
    """Process and filter deals."""
    ...
```

## Testing Guidelines

### Test Structure

```
tests/
├── govmap/          # Unit tests for govmap package
├── e2e/             # End-to-end integration tests
└── api_health/      # API health monitoring (weekly)
```

### Writing Tests

```python
import pytest
from nadlan_mcp.govmap.models import Deal

class TestYourFeature:
    """Test cases for your feature."""

    @pytest.fixture
    def sample_deals(self):
        """Create sample test data."""
        return [
            Deal(objectid=1, deal_amount=1000000, deal_date="2024-01-01"),
            Deal(objectid=2, deal_amount=1500000, deal_date="2024-02-01"),
        ]

    def test_basic_functionality(self, sample_deals):
        """Test basic functionality."""
        result = your_function(sample_deals)
        assert len(result) == 2
```

### Test Coverage

Aim for **>80% coverage** for new code:

```bash
pytest --cov=nadlan_mcp --cov-report=html
open htmlcov/index.html
```

### Running Different Test Suites

```bash
# Fast tests only (default, ~12s)
pytest tests/ -m "not api_health" -q

# Integration tests (makes real API calls)
pytest -m integration -v

# API health checks (weekly)
pytest -m api_health -v

# Specific test file
pytest tests/govmap/test_filters.py
```

## Architecture Guidelines

### Package Structure

```
nadlan_mcp/
├── govmap/              # Core business logic
│   ├── models.py        # Pydantic data models
│   ├── client.py        # API client
│   ├── filters.py       # Deal filtering
│   ├── statistics.py    # Statistical calculations
│   ├── market_analysis.py  # Market analysis
│   ├── validators.py    # Input validation
│   └── utils.py         # Helper functions
├── fastmcp_server.py    # MCP tool definitions
└── config.py            # Configuration management
```

### Design Principles

1. **MCP provides data, LLM provides intelligence**
   - Keep analysis simple in MCP layer
   - Let LLM interpret and reason about data

2. **Return Pydantic models, not dicts**
   - All API methods return typed models
   - Use `.model_dump()` to serialize for JSON

3. **Separation of concerns**
   - `client.py` - API calls only
   - `filters.py` - Filtering logic
   - `statistics.py` - Calculations
   - `market_analysis.py` - Analysis functions

4. **Backward compatibility**
   - Use `govmap/__init__.py` for public exports
   - Maintain existing function signatures

### Adding New Features

#### 1. Add Pydantic Model (if needed)

```python
# nadlan_mcp/govmap/models.py
class YourModel(BaseModel):
    """Your model description."""

    field_name: str = Field(..., description="Field description")
    optional_field: Optional[int] = Field(None, description="Optional field")
```

#### 2. Add Business Logic

```python
# nadlan_mcp/govmap/your_module.py
from typing import List
from .models import Deal, YourModel

def your_function(deals: List[Deal]) -> YourModel:
    """
    Your function description.

    Args:
        deals: List of Deal instances

    Returns:
        YourModel instance

    Raises:
        ValueError: If deals list is empty
    """
    if not deals:
        raise ValueError("Cannot process empty deals list")

    # Your logic here
    return YourModel(field_name="value")
```

#### 3. Add Client Method

```python
# nadlan_mcp/govmap/client.py
def your_method(self, param: str) -> YourModel:
    """
    Client method description.

    Args:
        param: Parameter description

    Returns:
        YourModel instance
    """
    # Implementation
    return your_function(data)
```

#### 4. Add MCP Tool

```python
# nadlan_mcp/fastmcp_server.py
@mcp.tool()
def your_mcp_tool(param: str) -> str:
    """
    MCP tool description visible to LLM.

    Args:
        param: Parameter description

    Returns:
        JSON string with results
    """
    try:
        result = client.your_method(param)
        return json.dumps({
            "result": result.model_dump(exclude_none=True)
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error in your_mcp_tool: {e}")
        return f"Error: {str(e)}"
```

#### 5. Add Tests

```python
# tests/govmap/test_your_module.py
def test_your_function():
    """Test your function."""
    deals = [Deal(...)]
    result = your_function(deals)
    assert isinstance(result, YourModel)
    assert result.field_name == "expected_value"
```

#### 6. Update Documentation

- Add to `API_REFERENCE.md`
- Add example to `examples/` if useful
- Update `README.md` if it's a major feature

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code formatted with Ruff
3. ✅ No Ruff warnings
4. ✅ Added tests for new features
5. ✅ Updated documentation

### PR Checklist

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added new tests
- [ ] All existing tests pass
- [ ] Tested manually

## Documentation
- [ ] Updated README.md (if needed)
- [ ] Updated API_REFERENCE.md (if needed)
- [ ] Added examples (if needed)
```

### Code Review

- PRs reviewed by maintainers
- Address feedback constructively
- CI checks must pass (Ruff + tests)

## Common Tasks

### Adding a New MCP Tool

See "Adding New Features" section above.

### Fixing a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify test now passes
4. Add regression test if needed

### Updating Dependencies

```bash
# Update requirements files
pip list --outdated
pip install <package> --upgrade
pip freeze > requirements.txt

# Test everything still works
pytest tests/ -m "not api_health"
```

### Running API Health Checks

```bash
# Weekly check that Govmap API still works
pytest -m api_health -v
```

## Questions?

- Create an issue for questions
- Check existing issues and PRs
- Read ARCHITECTURE.md for design decisions
- Review examples/ for usage patterns

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Nadlan-MCP!** 🎉
