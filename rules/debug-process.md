# Debugger Report Format

Shared output contract for the language debugger agents (`go-debugger`, `py-debugger`, `nvim-debugger`, `gherkin-debugger`). Each agent keeps its own language-specific diagnostic process and failure-mode tables; this rule owns only the report shape so it stays consistent across the family and is defined in exactly one place.

## Report shape

For every bug, report these four fields in order:

1. **Root cause** — the specific line and condition that triggers the failure (one sentence).
2. **Evidence** — the code references, state, step text, or variable that confirm the diagnosis.
3. **Fix** — the minimal change that resolves the issue.
4. **Regression risk** — what else could break and how to verify.
