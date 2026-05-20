# Architecture Decision Record Style

Format the response as an Architecture Decision Record. Use these section headings exactly, in this order:

**Context**
The forces in play that make this a decision rather than a default. Constraints, prior decisions, deadlines, stakeholder asks, technical limits. Two to five sentences. If a `CLAUDE.md` ICP, a deadline, or a compliance requirement is load-bearing, cite it.

**Options**
Every option considered, including "do nothing" if it was on the table. One bullet per option, in the form:

- **<Option name>** — one-line description — main trade-off (what it makes easier, what it makes harder).

If only one option was considered, that is itself a finding — say "No alternatives considered" and stop the ADR; the decision is not yet ready.

**Decision**
The chosen option, stated in one sentence in the imperative ("Use X for Y"). If a design pattern from `skills/patterns/design-patterns.md` applies, name it explicitly here — for example, "Apply the Strategy pattern to select routing algorithm because the signal is a large `switch` on algorithm variant."

**Consequences**
Three sub-points, each a bullet list:

- **Easier:** what this unlocks or simplifies.
- **Harder:** what this gives up or makes more expensive.
- **Locked in:** what becomes difficult to reverse — the migration cost if this decision is later wrong.

**Status**
One word, with date and author when relevant:

- `Proposed` — under discussion
- `Accepted` — committed, in effect
- `Superseded by <link or ADR id>` — replaced; do not delete the old ADR

No prose outside these sections. No "Summary" section. The Decision sentence is the summary.
