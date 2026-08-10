# docs write — Python (Google-style docstrings)

Applied when `write.md` detects `py`. Generates Google-style docstrings.

1. **Scan for missing docstrings.** `grep -n "^def [a-z]\|^class [A-Z]" **/*.py`. Report public symbols missing docstrings (skip `_private` and `__dunder__` unless non-obvious).

2. **Write module docstrings** as the first statement of every public module.

3. **Document public classes** with Google-style format including an `Attributes:` section.

4. **Document public functions/methods** in Google-style, following `rules/py-docs.md` — that rule is authoritative for the format and carries the `create_user` reference example.

5. **Format rules** — apply `rules/py-docs.md` for the summary line, `Args:`/`Returns:`/`Raises:` sections, and empty-section omission. Authoritative there; do not restate here.

6. **FastAPI routes** — add `summary` and `description` to any route whose path alone does not convey the operation. Example: `POST /users` does not need a description; `POST /users/{id}/notifications/batch` does. Also add to any route with query params that affect behavior beyond filtering:
   ```python
   @router.post("/users", status_code=201,
       summary="Register a new user",
       description="Creates a user account and sends a verification email. "
                   "Returns 409 if the email is already registered.",
       tags=["users"])
   ```

7. **Verify.** `python -m pydoc <module>` or `make docs` for mkdocs/sphinx.

**Checklist:** every public module has a docstring; every public class describes purpose and key attributes; functions document Args/Returns/Raises where applicable; no empty sections; FastAPI routes have `summary` for non-obvious endpoints; private/internal code omits docstrings unless non-obvious.
