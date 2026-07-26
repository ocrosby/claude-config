---
description: Unit tests verify behavior through the public surface, not implementation. Diagnostic: if refactoring internals breaks the test, the test measures shape not behavior. Mocks live at system edges (DB, HTTP, filesystem, clock), not at class edges inside your own module.
---

# Black-Box Unit Testing

Unit tests should verify **behavior through the public surface**, not the implementation underneath. A suite that couples to internal collaborators, private state, or method-level decomposition breaks on every refactor even when the code under test still does the right thing. The suite stops being a safety net and starts being an obstacle.

**Diagnostic question**: *"If I change how this code is written without changing what it does, will the test still pass?"* If the answer is no, the test measures implementation, not behavior.

**This is an intentional design decision — do not simplify it away.** "Just mock the collaborator" is fast to write and slow to live with. The extra 10–30 lines of an in-memory fake pay for themselves the first time someone refactors the collaboration.

## Priority order — shape before coverage before assertion strength

When writing or reviewing unit tests, work through these concerns **in this order**. Do not compromise an earlier concern to raise a later one.

1. **Shape and seams first.** The test is black-box; seams are drawn at system edges (external I/O, clock, queue, filesystem), not at class edges inside your own module. If a behavior is hard to reach from the outside, the seam is misplaced — redraw it. This is non-negotiable.
2. **Coverage second, as a detector.** Once shape is right, use line/branch coverage to find behaviors no test exercises. For each gap, add or extend a **black-box** test through the public surface. Never add a spy, an internal mock, or a private-field reach-in to raise a coverage number. If a line cannot be exercised from the outside, that is a design signal (dead branch, misplaced seam, or genuinely unreachable code), not licence to reach in. Coverage is a floor, not a target.
3. **Assertion strength third, on load-bearing modules.** Use mutation testing (see `rules/mutation-testing.md`) to check whether the assertions catch anything. Fix survivors by strengthening the outside-in assertion or adding the missing boundary case, never by pinning internals to kill the mutant.

The reason this order matters: coverage-chasing and mutation-score-chasing both push tests toward white-box shape when the ordering is inverted — the shortest path to an uncovered branch or a surviving mutant is often an internal reach-in. Locking shape in first is what keeps the optimization work net-positive.

## What "unit" means here

A unit is a **behavior**, not a class. A `Cart` that uses `Discount`, `Inventory`, and `TaxCalculator` to compute a total is one behavioral unit: "apply store rules and produce a total." The three collaborators are part of the mechanism, not separate units. Tests belong at the outside surface — incoming messages and observable outcomes.

Do not equate "the unit under test" with "the unit of code organization" (one class = one test file; one method = one test). That equivalence produces every white-box pattern below.

## Recognition Signals

### White-box shapes that couple to implementation

| Signal | Why it's white-box | Black-box alternative |
|---|---|---|
| Test asserts a specific method-level return value used to set up a *later* assertion (`cart.apply_discount()` returns a `Discount` object; test asserts on that object) | Refactoring `apply_discount` to a builder or a field breaks the test even though `total()` still returns the right number | Set up through the public API; assert only on the outside contract |
| Mocking a collaborator owned by the same team, in the same codebase, in the same deployable | Test pins the *shape of the collaboration*, not the observable outcome — inlining, moving, or re-splitting the collaborator breaks the test | Use the real collaborator; or a small in-memory fake at a genuine boundary |
| Assertion is "the ledger was called with a credit of 100" (behavior verification) instead of "the account balance is 100" (state verification) | Fowler's distinction: behavior verification pins the call sequence, state verification pins the outcome | Assert on the observable state after the operation |
| Reaching into private fields (`_items`, `_discount`) to arrange the scenario | Arrangement measures shape; the test cannot survive a change to internal storage | Construct through the public API — the same API a real caller uses |
| Coverage-chasing: the shortest path to an unreached branch is a spy or an internal reach-in | Line coverage rewards touching the line by any means; the reward mechanism actively pushes tests toward white-box | Either extend the black-box tests to genuinely exercise the branch, or leave it uncovered and record why |
| Testing every method individually — one `test_add_item`, one `test_apply_discount`, one `test_total`, one `test_checkout` | Method-level tests couple to method-level decomposition; extracting or inlining a method breaks a test whose behavior didn't move | Test the behavior end-to-end through the entry point |

### Legitimate exception — adapter tests at genuine system edges

At the boundary with an external system (Stripe, S3, a database driver, a message queue), **the interaction itself is the contract**. Asserting *"when I call `charge`, we POST to `/v1/charges` with `amount` and `currency` in the body"* is a black-box test of a narrow contract expressed in outbound messages. The adapter's job *is* making exactly that call.

This is why the rule is **"mock at system edges, not class edges."** Seams aligned with external systems justify interaction-verification tests. Class-level seams inside your own module do not.

## Mandatory Behaviors

**When writing a new unit test**:

1. **Name the behavior first**, before writing setup. "Given X, when Y, then Z." If the sentence names a collaborator ("Given `Discount` returns 10%..."), the test will be white-box. Rephrase in terms of observable outcomes ("Given 3 books at $20 with the bulk-discount policy...").
2. **Set up through the public API.** If arrangement requires reaching into private fields or calling `_internal` methods, it is measuring shape.
3. **Assert on outcomes, not traces.** Prefer "the account balance is 100" over "the ledger was called with a credit of 100."
4. **Use real collaborators when they are same-team, deterministic, and fast.** Save mocks for edges.
5. **Prefer a fake to a mock at a stateful boundary.** A 10–30 line in-memory repository is cheaper across the codebase's lifetime than per-test mock ceremony, and makes state assertions natural.
6. **When asserting on calls, ask *why*.** Sometimes the answer is "this is a genuine adapter-shaped contract." More often the answer is "I drew the boundary at the wrong seam." The question is diagnostic — do not skip it.

**When editing an existing test**: if the change would tighten it against implementation detail (add a spy, mock a collaborator you own, reach into a private field to arrange), stop. Rework the test through the public API or leave it alone.

**When reviewing code**: apply the severity buckets from `rules/findings-format.md`.

- **Must Fix**: a test that mocks a collaborator the same team owns *and* asserts on the call rather than the outcome (guarantees the test breaks on any collaboration refactor).
- **Should Fix**: a test that reaches into private fields for setup; a test that asserts on method-level return values instead of end-to-end outcomes; a coverage-driven test that spies on an internal seam.
- **Consider**: a test that could be tightened to a state assertion but currently uses a call assertion at a genuine adapter boundary.

## The refactoring-loop diagnostic

The best measure of test-suite health is not coverage percentage or mutation score. It is what happens when someone **refactors code without changing behavior** (extract helpers, move methods, inline collaborators, swap internal data structures) and then runs the tests.

- Tests still pass → the suite is testing behavior
- Tests fail → the suite was describing implementation

Run this deliberately every few weeks on a module you own. Every refactor is a chance to notice which tests fought back and either loosen them or redraw the boundary. Silent drift toward white-box happens otherwise — one small "just spy on that method" at a time.

## Kent Beck's Desiderata (the two that anchor this rule)

Beck lists several properties good tests should have; two of them determine whether the suite survives the code it covers:

- **Behavioral** — tests describe *what* code does, not *how*
- **Structure-insensitive** — tests do not change when the code's structure (class layout, method decomposition, collaborator wiring) changes without changing behavior

The other desiderata (isolated, readable, specific, predictive, inspiring) matter, but the two above are what black-box discipline directly buys.

## Pragmatism Guard

- **Adapter tests at real system edges** justify interaction-verification. Do not apply this rule against a well-scoped Stripe/S3/DB-driver adapter whose job *is* to produce a specific outbound message.
- **A targeted spy for a specific bug** (e.g., "the retry loop must not call the downstream more than N times") is a legitimate call assertion — but it lives alongside the state-verification tests, not instead of them.
- **Testing genuinely-private complex logic in isolation** may occasionally warrant a same-package test in Go or a direct-import test in Python. Use it sparingly and mark it with a one-line comment naming *why* the public surface is not sufficient.
- **Legacy code with no seams** may not survive a full black-box rewrite in one pass. Use characterization tests through the widest available public API as a bridge; migrate to black-box shape as the code becomes testable. See `rules/tdd.md`.

## Anti-Patterns to Avoid

- **Coverage-chasing that mocks internals.** Coverage rises; refactorability falls. Net-negative.
- **"Method-per-test" harnesses** that mirror the class's method list. This is not test organization — it is white-box coupling by convention.
- **Mock-heavy suites that validate mock wiring.** If the assertion reads like "the mock received this call in this order," the test measures the mock, not the code.
- **Removing black-box tests because they "duplicate" white-box tests.** The black-box tests survive refactors; the white-box tests do not. Delete the white-box tests instead.
- **Chasing mutation score with implementation-pinning tests.** See `rules/mutation-testing.md` — mutation score achieved by mocking internals is net-negative work that looks positive on a dashboard.

## Cross-references

- `rules/tdd.md` — TDD workflow (red-green-refactor). Black-box discipline is about test *shape*; TDD is about test *timing*. They compose.
- `rules/mutation-testing.md` — mutation testing measures whether assertions are strong. High mutation score achieved by mocking internals is net-negative — see the mutation-testing rule for how to pursue mutation score without violating this one.
- `rules/py-testing.md`, `rules/go-testing.md`, `rules/nvim-testing.md` — language-specific test conventions. This rule applies on top of them.
