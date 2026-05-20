---
description: Python-specific security idioms — library calls and patterns. The general signal table lives in owasp-top-10.md.
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---

# Python Security Idioms

> See `owasp-top-10.md` for the general signal table and mandatory behaviors. This file lists the Python-specific *how*.

- **Secrets**: `pydantic_settings.BaseSettings` + `SecretStr`. `get_secret_value()` is the only extraction path; `str()`/`repr()` return `'**********'`.
- **Subprocess**: `subprocess.run(["cmd", "--", user_input], check=True)`. Never `shell=True` with dynamic input.
- **Deserialization**: never `pickle.loads` on untrusted input. `yaml.load` → `yaml.safe_load`. Prefer JSON + Pydantic.
- **Input validation**: Pydantic at every boundary; set `model_config = ConfigDict(extra="forbid")` where strictness matters. Never pass raw dicts into domain logic.
- **Path traversal**: `(base / user_path).resolve()` then check `base == target or base in target.parents`.
- **Constant-time compare**: `hmac.compare_digest`. Never `==` on secrets, signatures, or HMACs.
- **JWT**: `jwt.decode(token, key, algorithms=["RS256"])`. Pin `algorithms` (blocks `alg: none` and key confusion); never `verify_signature=False` in production.
- **Password hashing**: `passlib.context.CryptContext(schemes=["argon2"])` or `argon2.PasswordHasher()`. Never `hashlib.sha256`.
- **Dependencies**: pin in `pyproject.toml`, lock with `uv lock`, run `pip-audit` in CI as a build gate.
