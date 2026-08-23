# Coverage Report Tooling

**When configuring a workflow that renders coverage as HTML, use `genhtml` from the `lcov` package. Do not use ReportGenerator (`dotnet tool install --global dotnet-reportgenerator-globaltool`).**

This is a user preference for consistency across every repository in this account. Yoda (`yoda.nvim`) is the canonical setup — every other repo's badge workflow follows the same shape unless there's a specific reason not to.

## Recognition Signals

| Signal | Correct action |
|---|---|
| A `.github/workflows/*.y{a,}ml` job renders coverage → HTML for GitHub Pages | Emit LCOV, install `lcov` via `apt-get`, run `genhtml` |
| Coverage source is `go test -coverprofile=coverage.out` | Convert to LCOV via `github.com/jandelgado/gcov2lcov`, then `genhtml` |
| Coverage source is a Lua test runner (`neospec`, `plenary`) | LCOV is already produced natively; go straight to `genhtml` |
| Coverage source is `pytest --cov` | Emit LCOV via `pytest --cov --cov-report=lcov:coverage/lcov.info`, then `genhtml` |
| An existing workflow already uses `reportgenerator` / `dotnet-reportgenerator-globaltool` | Swap it out for the `genhtml` path above |

## Mandatory Behaviors

**When authoring a new coverage-HTML workflow:** use `genhtml`. The canonical two-step recipe is:

```yaml
- name: Install lcov
  run: sudo apt-get install -y --quiet lcov
- name: Generate HTML coverage report
  run: genhtml coverage/lcov.info -o htmlcov/ --quiet --ignore-errors source --title "<Project> Coverage"
```

**When editing an existing workflow that renders coverage:** if you see any of the following, swap them out for the recipe above in the same change:

- `dotnet tool install --global dotnet-reportgenerator-globaltool`
- `reportgenerator -reports:... -reporttypes:Html`
- Any `dotnet-*` install whose only purpose is coverage HTML

**When reviewing a workflow:** a `reportgenerator` invocation without a stated exception is a **Must Fix** — swap for `genhtml`. A future `dotnet-reportgenerator-globaltool` reappearing after removal is a regression; flag as **Must Fix** with a pointer to this rule.

**Why:** consistency with `yoda.nvim`; one fewer runtime in every CI job (`.NET` SDK download is ~200 MB, `lcov` is ~3 MB); `genhtml` is a standard Linux tool, requires no version pinning against a moving dotnet-tool version.

**How to apply:** any Go / Python / Lua / mixed-language CI job that publishes an HTML coverage report — plugin repos, distribution repos, backend services, personal projects. The rule covers HTML rendering only; formatting the underlying coverage as LCOV / Cobertura / Coveralls for OTHER consumers (Codecov, coverage-badge actions) is independent and unaffected.

## Pragmatism Guard

Do not apply this rule when:

- **The workflow is not Ubuntu / Debian-based** and `apt-get install lcov` won't work. Use the platform's equivalent (`brew install lcov` on macOS runners, `apk add lcov` on Alpine). If no `lcov` package exists on the platform, name the constraint and pick the smallest-footprint alternative — `.NET` still last.
- **The project already publishes to a service that owns the HTML rendering** (Codecov, Coveralls). Neither `genhtml` nor `reportgenerator` is needed; upload the LCOV or Cobertura and let the service render.
- **The workflow is a proof-of-concept spike** that will be deleted within days. Whatever ships fastest.

## Anti-Patterns to Avoid

- **Reaching for `reportgenerator` because a Go coverage.xml is already produced.** The LCOV path is one extra tool (`gcov2lcov`) that is smaller and faster than the .NET SDK download.
- **Copying an old badge workflow verbatim from a template that predates this rule.** Cross-check every `.github/workflows/*.yml` against this rule when copying between repos.
- **"But .NET is already installed."** Not a reason. If the rest of the job doesn't use .NET, the runtime install is pure overhead.
