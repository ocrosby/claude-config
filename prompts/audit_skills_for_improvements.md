# Audit Skills for Improvements

Audit every skill in my project. For each one:

Flag what's missing or weak and suggest improvements:

- Is there a deterministic part that should be a script?
- Is there a templated output that should live in `assets/`?
- Is there a config value being re-entered that should live in `config.json`?
- Would `AskUserQuestion` clean up multiple-choice setup?
- Should it accept an `arguments` frontmatter field for invocation-time inputs (slug, file path, target)?

For each, suggest how we can improve them and what changes would be needed.
