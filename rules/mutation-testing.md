---
description: Grades assertion strength by seeding small faults and counting surviving mutants — a killed mutant means the tests would catch the bug. Gate CI on 'no new survivors in the diff', never a percentage floor. Tools: mutmut (Python), gremlins (Go), cargo-mutants (Rust).
---

# Mutation Testing

Line coverage tells you where tests have not been. It does not tell you whether tests would catch a bug if the code were wrong. Mutation testing closes that gap by **grading the tests, not the code**: seed small, syntactically-valid faults into the source, run the suite, and count how many faults survive. A surviving mutant is a specific counter-example — a version of the code the suite would ship without noticing.

**This is an intentional signal, not a target — do not simplify it into a percentage gate.** Chasing a mutation-score number with tests that pin implementation detail raises the score and lowers the suite's survivability. See `rules/black-box-testing.md`; mutation score is only meaningful when the underlying tests are black-box.

**Order matters: shape → coverage → mutation score.** Do not reach for mutation testing before the suite is black-box and coverage has been closed with black-box tests. Running mutmut / gremlins / cargo-mutants on a white-box suite tells you which internal reach-ins to add, which is exactly the wrong direction. The priority order lives in `rules/black-box-testing.md`; this rule is the third step, not the first.

## Definitions

- **Mutant**: a version of the source with one small syntactic change — a boundary flipped (`>=` → `>`), an operator changed (`+` → `-`), a Boolean inverted, a return value replaced with a plausible constant, an entire function body replaced with a default value.
- **Killed mutant**: at least one test fails against the mutated code. Good.
- **Survived mutant**: every test still passes against the mutated code. Bad — the suite would not have caught this bug.
- **Mutation score**: killed / (killed + survived), expressed as a percentage.

The theory rests on two 1978 results from DeMillo, Lipton, and Sayward that have held up empirically for 50 years:

- **Competent Programmer Hypothesis (CPH)** — real bugs are small, close-to-correct edits, so small mutations catch most bugs a competent programmer ships.
- **Coupling Effect** — tests that catch small mutations tend to catch complex bugs built from them.

## Recognition Signals — what a surviving mutant reveals

| Survivor shape | Diagnosis | Fix |
|---|---|---|
| Function returns a value; no test asserts on it | **Assertion gap** — test executes the code but does not check the result | Add an assertion on the return value |
| Boundary flip survives (`>=` → `>`) while tests exist strictly-inside and strictly-outside the boundary | **Boundary blindness** — the single most common finding on healthy codebases; good coverage numbers actively hide it | Add a test *at* the boundary, not just around it |
| Return value replaced with a value of the same shape survives (`return x` → `return default`) | **Over-broad assertion** — test asserts `is not None` or `err == nil` instead of the actual value | Assert on the value, not just the shape |
| Every mutation in a branch survives | **Dead branch** — no test reaches it | Add a test that reaches it, or delete the branch if it is genuinely unreachable |
| A line's mutations all survive but the line is exercised | **Redundant code** — the line does nothing observable | Delete the line, or find the missing assertion that should have depended on it |
| Happy-path mutations killed; error-path mutations survive (or vice versa) | **Untested error/happy path** | Add the missing side's test |
| Field-level mutations survive on a struct/record while other fields are killed | **Weak assertion on structured data** — test asserts one field, ignores the rest | Assert on the whole value, or on every field that matters |

The **shape of the survivor list matters more than the count**. Ten survivors clustered in one function is "this function is under-tested." Ten survivors scattered across a module is "diffuse assertion weakness" — a design-level conversation, not a per-line fix.

## What mutation testing does NOT tell you

- **Whether the specification is right.** If the code implements the wrong behavior and the tests match, mutation score is 100% and the product is still wrong.
- **Whether the tests are black-box.** Brittle, implementation-pinning tests can achieve high mutation scores and still fight every refactor. Mutation score is orthogonal to test shape — check with the refactoring-loop diagnostic in `rules/black-box-testing.md`.
- **Whether the design is sound.** Tangled, cohesion-poor modules can score high.
- **Race conditions, performance, or security properties** the tests do not explicitly check.

## Mandatory Behaviors

**When to use mutation testing** (in order of value):

1. **Newly-written business logic** — assertions are freshest; the signal is highest.
2. **Pure-logic modules where correctness matters** — pricing, permissions, validators, parsers, state machines with boundaries and conditionals.
3. **Legacy modules just inherited** — one archaeological run; the survivor list is a prioritized map of where the previous team's assertions were weak.
4. **Before removing a test you suspect is worthless** — run with and without the test; if the score does not change, the test catches nothing others do not.
5. **On PR diffs, in CI** — the only economically viable mode on any real suite. Full-repo runs are for one-off archaeology.
6. **As a code-review conversation-starter** — "should this specific mutant be caught?" is a better prompt than "should this have more tests?"

**When NOT to use it**:

- **Coverage below ~60–70%** — you will rediscover what a coverage report already shows.
- **Flaky suites** — "unchanged code passes; mutated code fails" is the entire signal; flakiness destroys it.
- **Slow I/O-dominated suites** — a 45-minute suite × 5,000 mutants = 150 days of runtime. Use `--in-diff` or isolate the fast unit tests first.
- **Mostly-configuration or framework-glue code** — produces `NOT VIABLE` mutants and noise.

**How to gate on it in CI**:

- ✅ Gate on **"exit non-zero if any surviving mutants in the diff"**.
- ❌ Do **not** gate on a percentage floor for the whole repo. The failure mode is tests-that-pin-implementation-detail, which is worse than the original problem.
- **Ratchet strictness over quarters, not sprints.** Jumping from 60% → 80% in a sprint produces a rush of brittle tests.

**How to interpret the score as a shape, not a number**:

- **90%+ on pure-logic code** (validators, parsers, pricing, permissions) → strong signal; tests are well-asserted.
- **60–80% on service code with I/O** → often the realistic ceiling before tests start pinning implementation. Aim here and stop.
- **Below 40% anywhere** → something specific is wrong. Read the survivor list; do not add tests blindly.

**When reviewing code**: apply the severity buckets from `rules/findings-format.md`.

- **Must Fix**: a new function or state machine ships with tests that leave every operator/boundary mutation surviving (the tests do not check anything the suite would notice).
- **Should Fix**: the PR raises the module's mutation score by mocking internals or spying on private methods — the score is up, the suite is worse. See `rules/black-box-testing.md`.
- **Consider**: a survivor list clusters in one function that could be split or made more assertable, but the current tests are not wrong.

## Tools

| Language | Tool | Config | Notes |
|---|---|---|---|
| Python | `mutmut` v3 (Anders Hovmöller) | `[tool.mutmut]` in `pyproject.toml` | Wraps pytest. `uv run mutmut run` / `uv run mutmut browse` (TUI, press `r` to retest). Needs `fork()` — runs on macOS/Linux, WSL on Windows. |
| Go | `gremlins` (pin the version) | `.gremlins.yaml` | `gremlins unleash`; filter noise with `--output-statuses lc`; diff mode `--diff origin/main`. Only mutates *covered* code — the score is over reached code, not all code. Run per-package on large modules. |
| Rust | `cargo-mutants` (Martin Pool) | `.cargo/mutants.toml` | `cargo mutants`; diff mode `cargo mutants --in-diff <(git diff origin/main)`. The **"replace function body with value"** mutator catches `is_ok()`-only assertions — leave it enabled. Configure `error_values` once baseline is stable to unlock `Err(...)` mutations. |

Install commands and detailed flags live in the tool's own docs; the important choice is *which* tool, not which flag. All three generate similar mutations and reward the same interpretation loop.

## Pragmatism Guard

- **Do not chase a percentage target for its own sake.** Adding tests that assert on internal state directly raises the score and couples to implementation — net-negative work looking positive on the dashboard.
- **Do not run mutation testing on a suite you would not run coverage on.** If the tests are flaky or too slow to run per-PR, mutation testing will amplify both problems.
- **Do not use mutation score as a hiring/team metric.** It is a diagnostic for individual modules, not a proxy for team quality.

## Anti-Patterns to Avoid

- **Percentage gates in CI.** Guarantees the rush-to-brittle-tests failure mode. Gate on "no new survivors in the diff" instead.
- **Full-repo runs on every push.** Economically infeasible on any real suite; treat full runs as one-off archaeology.
- **Reading only the score, not the survivor list.** The shape and clustering of survivors is the actual signal.
- **Adding a test whose sole purpose is to kill one mutant.** If the surviving mutant does not correspond to a real behavior the caller relies on, deleting the code is often the better fix.

## Cross-references

- `rules/black-box-testing.md` — **required reading** before pursuing a mutation-score target. Pursuing mutation score without black-box discipline pins implementation detail and makes the suite worse.
- `rules/tdd.md` — mutation testing is not TDD; it is a *retrospective* signal on tests that already exist. Both compose — write the test first (TDD), then use mutation testing to check whether the assertion is load-bearing.
