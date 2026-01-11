# Pytest Guide - Backend Testing

## Test Structure

```
tests/
├── unit/           # Module-level tests
├── integration/    # Cross-module tests
├── e2e/            # End-to-end workflows
├── security/       # Security-specific tests
├── api/            # API simulation tests (need server)
└── fixtures/       # Test data
```

---

## Running Tests

### Without Server (Unit/Integration)
```bash
python3 -m pytest tests/ -v
```

### With Server (TRUE Simulation)
```bash
# Start server
python3 scripts/create_admin.py
python3 server/main.py &
sleep 5

# Run ALL tests including API
RUN_API_TESTS=1 python3 -m pytest -v

# API tests only
RUN_API_TESTS=1 python3 -m pytest tests/api/ -v
```

---

## Test Categories

| Directory | Tests | Server Needed? |
|-----------|-------|----------------|
| `tests/unit/` | 350+ | No |
| `tests/integration/` | 110 | No |
| `tests/e2e/` | 115 | No |
| `tests/security/` | 86 | No |
| `tests/api/` | 168 | **Yes** |

---

## Writing Tests

### Unit Test Example
```python
import pytest
from server.utils.auth import hash_password, verify_password

def test_password_hashing():
    password = "test123"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)
```

### API Test Example
```python
import pytest
import requests

API_URL = "http://localhost:8888"

@pytest.mark.skipif(
    os.environ.get("RUN_API_TESTS") != "1",
    reason="API tests need running server"
)
def test_login_endpoint():
    response = requests.post(f"{API_URL}/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

---

## Coverage

```bash
# Generate HTML report
python3 -m pytest --cov=server --cov-report=html

# View report
open htmlcov/index.html
```

Current: **53%** (target: 80%)

---

## Fixtures

Test data in `tests/fixtures/`:
- `sample_language_data.txt` - Korean/English pairs
- `sample_quicksearch_data.txt` - Dictionary data
- `sample_to_translate.txt` - Translation test data
