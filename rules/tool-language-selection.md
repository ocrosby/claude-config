# Tool Language Selection

Choosing the implementation language for a new CLI, developer tool, or editor-adjacent binary is a routine decision that has long-lived consequences: distribution model, contributor pool, ecosystem-consistency signal to the target audience, and how much of the tool's stated goal the language actively helps or fights.

This rule captures the decision matrix so the same considerations get applied every time a new tool is scoped, rather than defaulting to whichever language the author last used.

**Scope:** applies when scoping a *new* standalone tool — a Go/Rust/Zig binary, a CLI, a language server, a linter/formatter, a code generator, a build-time transformer. Does not apply to:

- Application code inside an existing service (use the service's language)
- Extensions/plugins for an existing runtime (Neovim plugin → Lua; VS Code extension → TypeScript; etc.)
- One-off scripts or research spikes (whatever ships fastest)

## Recognition Signals

### When Rust is the right pick

| Signal | Why Rust wins |
|---|---|
| Tree-sitter parsing is central to the tool's job | Idiomatic Rust bindings; the reference implementations of every modern Lua/JS/TS linter (`stylua`, `selene`, `oxc`, `biome`) live in Rust |
| Performance-sensitive scans over many files (linter, formatter, indexer, code search) | Zero-cost abstractions + no GC pause; measurable 5–10× advantage over Go on AST-heavy workloads |
| The tool joins a "shelf" (ruff/uv, biome/oxlint, stylua/selene) where the ecosystem is Rust | Ecosystem-consistency is a trust signal to the audience already using neighboring tools |
| Long-lived foundational infrastructure ("this must still be correct in 5 years") | Type system + ownership model catch a class of defects at compile time that would ship in Go |
| Full-text indexing, embedded database, or vector search | `tantivy`, `sled`, `qdrant-client` outclass their Go equivalents |
| Producing a WASM artifact for browser/deno/plugin consumption | Rust → WASM is production-grade; Go's WASM story is workable but heavier |

### When Go is the right pick

| Signal | Why Go wins |
|---|---|
| CI plumbing dominates: HTTP downloads, subprocess orchestration, cross-platform binary distribution | Standard library covers it; Rust needs `reqwest` + `serde` + `tokio` + `cross` or `cargo-zigbuild` to reach parity |
| Sharing code with an existing Go tool in the same portfolio | Package import beats FFI or "rewrite the shared piece twice" |
| Cross-compilation to Windows is a hard requirement and must be trivial | `GOOS=windows GOARCH=amd64 go build` vs Rust's cross-compile ceremony |
| Kubernetes/cloud-native ecosystem (operators, controllers, sidecars, CRDs) | client-go, controller-runtime, Prometheus SDK, OpenTelemetry — Rust equivalents exist but are less mature |
| Build times matter for the contributor loop | `go build` in seconds; `cargo build` in minutes on first run |
| Time-to-first-ship dominates the tool's early value | Go's smaller standard library and single-way-to-do-it culture ships faster |

### Language-agnostic — pick whichever ships tomorrow

| Signal | Notes |
|---|---|
| Templating / scaffolding tool | Neither language wins; go with what you know |
| Tool < ~2000 LOC with modest I/O and no parsing | Aesthetic choice, no meaningful performance ceiling |
| Wrapper around a CLI that already exists (git, kubectl, docker) | Whichever ships the wrapper faster |
| Internal one-off / short-lived tooling | Bash/Python often beats both |

## Mandatory Behaviors

**When recommending a language for a new tool:** explicitly cite one or more signals from the tables above. A recommendation without a named signal is a preference, not a decision — flag your own recommendation if you can't cite one.

**Acknowledge path-dependence separately from first-principles fit.** If a tool exists in Go and the extension is trivially Go, say "Go — path-dependent on the existing binary" rather than presenting it as the first-principles pick. Two different arguments; don't conflate them.

**When path-dependence and first-principles fit disagree**, name both explicitly:

> First-principles pick: Rust (tree-sitter parsing + joins the stylua/selene shelf).
> Path-dependent pick: Go (extends existing binary X; sharing the download cache).
> Recommendation: [X] because [reason].

This is the honest form of the recommendation. It preserves the reasoning for future readers even when the pick reverses under different constraints.

**Consider audience ecosystem-consistency as a first-class signal**, not a marketing afterthought. A tool for the Neovim ecosystem shipped in Rust signals "I read the room" because every reference-quality Neovim CLI (stylua, selene, oxlint-for-lua) is Rust. Same tool in Go signals "author has Go elsewhere and stayed there." Neither is wrong, but the signal is real and worth naming.

**When reviewing a tool proposal**, flag as findings per `rules/findings-format.md`:

- **Must Fix**: language pick contradicts a named signal (e.g., "AST-heavy linter over many files, chose Go for shipping speed" — the shipping-speed argument is real but must be surfaced, not hidden)
- **Should Fix**: recommendation cites no signal, or defaults to "the author's usual language" without acknowledging alternatives
- **Consider**: the picked language is fine but a sibling language would signal better ecosystem-fit; note it and move on

## Pragmatism Guard

Do not apply this rule when:

- **The author has zero proficiency in the "correct" language and shipping matters.** A 3–6 month proficiency tax to learn Rust for the "right" pick is often the wrong trade against shipping in the language you already know. Name the trade explicitly rather than pretending it isn't there.
- **The tool is a spike or research prototype.** First-principles language fit matters for tools that will exist in 5 years. It does not matter for tools that will be thrown away in 2 weeks.
- **The organization has a mandated language standard.** Follow the standard; note the deviation from first-principles in an ADR.
- **The tool is one file with < 500 lines.** Language choice is aesthetic at this scale.

## Anti-Patterns to Avoid

- **"Ecosystem trend" as the sole argument.** "Everyone uses Rust now" is not a decision — cite a signal (tree-sitter, performance, shelf-membership) or don't invoke Rust.
- **Path-dependence dressed as first-principles.** If the real reason is "the sibling tool is Go, so this must be Go too," say that. Do not manufacture performance arguments to justify a pre-decided pick.
- **Rewriting a working Go tool in Rust for aesthetic reasons.** The rewrite cost is real. Only rewrite if a signal from the Rust table applies *and* the current tool has a concrete pain point that language change would relieve.
- **Choosing Rust for CI plumbing.** HTTP + subprocess + JSON is what Go's standard library was built for. Rust here means writing three lines of `Cargo.toml` deps for what Go does with `import "net/http"`. The AST/performance advantages that justify Rust do not apply to CI orchestration.
- **Choosing Go for a tool that will parse source code across large repos.** The performance ceiling matters here; if the tool succeeds it will scan millions of lines. Rust's advantage compounds over the tool's lifetime.

## When applied to Neovim-adjacent tools specifically

The Neovim ecosystem has an unusually strong Rust bias for adjacent tooling because the reference implementations of Lua tools are all Rust:

- Formatters: `stylua`
- Linters: `selene`
- Language servers: `lua-language-server` is C++, but the Neovim-consuming layer is universally Rust in new work
- Full-text search / AST tools: `oxc`, `biome` (JS/TS) set the shelf expectation

**Rust is the default for Neovim CLI tools that parse Lua, format Lua, lint Lua, or index Lua.** Go is the default for Neovim CLI tools that download binaries, orchestrate subprocesses, or wrap external CLIs (test runners, coverage tools, CI orchestrators).

Inside Neovim itself — plugin code — is always Lua. Rust ffi via `nvim-oxi` is a specialized tool for performance-critical inner-loop work (e.g., `rofl.nvim`), not a default.
