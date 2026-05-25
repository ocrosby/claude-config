#!/usr/bin/env python3
"""Emit the GoF design-pattern recognition signals table as structured JSON.

The signals are sourced from rules/design-patterns-application.md (a prose
rule) and codified here so /patterns can consume them without re-parsing
prose every invocation. The signal-to-code matching itself stays in Claude's
hands — only the catalog moves to a script.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import cli as _cli  # noqa: E402  # type: ignore[import-not-found]

SIGNALS: list[dict] = [
    # Creational
    {"pattern": "Builder", "category": "creational", "signal": "Constructor with 5+ parameters, especially optional ones"},
    {"pattern": "Factory Method", "category": "creational", "signal": "`new ConcreteType()` calls scattered across callers"},
    {"pattern": "Abstract Factory", "category": "creational", "signal": "Creating families of related objects that must be compatible"},
    {"pattern": "Prototype", "category": "creational", "signal": "Complex object copied with minor variations; template instances"},
    {"pattern": "Singleton", "category": "creational", "signal": "One globally-shared resource (config, connection pool, registry)"},
    # Structural
    {"pattern": "Adapter", "category": "structural", "signal": "Third-party or legacy interface does not match your domain contract"},
    {"pattern": "Bridge", "category": "structural", "signal": "Class hierarchy growing in two independent dimensions"},
    {"pattern": "Composite", "category": "structural", "signal": "Recursive tree where leaf and container must be treated identically"},
    {"pattern": "Decorator", "category": "structural", "signal": "Optional behaviors that combine in many permutations"},
    {"pattern": "Facade", "category": "structural", "signal": "Complex subsystem requiring multi-step initialization to use"},
    {"pattern": "Flyweight", "category": "structural", "signal": "Thousands of similar objects exhausting memory"},
    {"pattern": "Proxy", "category": "structural", "signal": "Cross-cutting concerns (caching, auth, logging, lazy init) around an object"},
    # Behavioral
    {"pattern": "Chain of Responsibility", "category": "behavioral", "signal": "Sequential pipeline of handlers; order or set changes at runtime"},
    {"pattern": "Command", "category": "behavioral", "signal": "UI action decoupled from business logic; undo/redo needed"},
    {"pattern": "Iterator", "category": "behavioral", "signal": "Collection traversal abstracted from the underlying data structure"},
    {"pattern": "Mediator", "category": "behavioral", "signal": "Many components with direct circular dependencies on each other"},
    {"pattern": "Memento", "category": "behavioral", "signal": "Object state snapshot needed for undo/rollback without exposing internals"},
    {"pattern": "Observer", "category": "behavioral", "signal": "Multiple listeners to a single event source; dynamic subscription"},
    {"pattern": "State", "category": "behavioral", "signal": "Large `switch`/`if` on an internal state field driving behavior"},
    {"pattern": "Strategy", "category": "behavioral", "signal": "Large `switch`/`if` selecting an algorithm variant"},
    {"pattern": "Template Method", "category": "behavioral", "signal": "Multiple classes sharing the same algorithm skeleton with minor variation"},
    {"pattern": "Visitor", "category": "behavioral", "signal": "New operations needed on a fixed class hierarchy without modifying it"},
]

# Language-specific implementation hints (sourced from rules/design-patterns-application.md).
LANGUAGE_NOTES: dict[str, list[dict]] = {
    "go": [
        {"pattern": "Builder", "note": "Use a `Config` struct or functional options — both are idiomatic Builder variants"},
        {"pattern": "Factory Method", "note": "Constructor functions (`NewX`) returning interfaces"},
        {"pattern": "Singleton", "note": "`sync.Once` for thread-safe lazy initialization"},
        {"pattern": "Observer", "note": "Channels are first-class — prefer channel-based pub/sub over callback registries"},
        {"pattern": "Decorator", "note": "Embed the interface, override specific methods, delegate the rest"},
    ],
    "py": [
        {"pattern": "Strategy", "note": "First-class functions and `Protocol` make this lightweight — a callable often suffices"},
        {"pattern": "Decorator", "note": "Python's `@decorator` syntax maps directly — use for cross-cutting concerns"},
        {"pattern": "Singleton", "note": "Module-level instances are effectively singletons; prefer DI over class-level enforcement"},
        {"pattern": "Builder", "note": "Dataclasses with `__post_init__` validation, or a dedicated builder class for complex construction"},
    ],
    "lua": [
        {"pattern": "Factory Method", "note": "Module-level constructor functions (`M.new(opts)`) returning tables with methods"},
        {"pattern": "Singleton", "note": "Module-local tables with lazy initialization via `if not M._state then ... end`"},
        {"pattern": "Observer", "note": "`nvim_create_autocmd` groups are Neovim's built-in Observer — prefer autocmds over callback registries"},
        {"pattern": "Strategy", "note": "Function tables (`local strategies = { lsp = ..., treesitter = ... }`) with a dispatch key"},
        {"pattern": "State", "note": "A `state` field in the module table with a dispatch table keyed by state name"},
        {"pattern": "Decorator", "note": "Wrap a module function, calling the original and adding before/after behavior"},
    ],
}


def main() -> int:
    parser = _cli.make_parser(__doc__)
    parser.add_argument("--category", choices=["creational", "structural", "behavioral", "all"], default="all")
    parser.add_argument("--language", choices=["go", "py", "lua"], default=None)
    args = parser.parse_args()

    signals = SIGNALS if args.category == "all" else [s for s in SIGNALS if s["category"] == args.category]
    payload: dict = {"signals": signals}
    if args.language:
        payload["language_notes"] = LANGUAGE_NOTES.get(args.language, [])
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
