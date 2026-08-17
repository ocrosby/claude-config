---
description: Python documentation: Google-style docstrings on all modules/classes/functions, `Args`/`Returns`/`Raises` sections (omit empties), FastAPI route `summary` and `description` for non-obvious endpoints. Fires on `**/*.py`.
paths:
  - "**/*.py"
  - "**/docs/**/*.md"
---

# Python Documentation

## Docstrings

- Use Google-style docstrings on all modules, classes, and functions — public and private alike

### Format

```python
def create_user(name: str, email: str, role: str = "member") -> User:
    """Create a new user and send a welcome notification.

    Args:
        name: Display name for the user.
        email: Email address — must be unique.
        role: Authorization role. Defaults to "member".

    Returns:
        The newly created user with a generated ID.

    Raises:
        DuplicateEmailError: If the email is already registered.
        ValidationError: If the email format is invalid.
    """
```

### Rules

- First line is a concise imperative summary (no period unless multi-sentence)
- `Args:` — one line per parameter, type info lives in the signature not the docstring
- `Returns:` — describe what is returned, not the type
- `Raises:` — list exceptions the caller should handle
- Omit sections that don't apply (no empty `Args:` blocks)

## README

Required sections, explanation quality, and example verification are owned by `rules/readme-standard.md`. Follow it — do not re-derive a shorter section list here. Python-specific content only:

- Installation shows `uv sync`; Usage shows how to run the application
- Configuration documents every environment variable and its default

## API Documentation

- FastAPI apps use Pydantic model docstrings and field descriptions for auto-generated OpenAPI docs
- Add `summary` and `description` to route decorators for non-obvious endpoints
- Tag routes with `tags=["domain"]` for logical grouping in the docs UI
