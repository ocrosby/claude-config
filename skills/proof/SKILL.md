---
description: Use when the user says "prove it", "cite that", "back that up", "where did you get that", "is that documented", or "show me the source" — or when about to assert a non-obvious technical fact (a flag, an API behavior, a config default) without a citation in hand. Forces a real citation or an explicit downgrade — never a fabricated one.
when_to_use: User says "prove it", "cite that", "where did you get that", "back that up", "is that documented", "show me the source", or invokes `/proof` explicitly. Also use proactively when you're about to assert something non-obvious (a flag exists, a function behaves a certain way, a config option is on by default) and you're not 100% certain.
disable-model-invocation: true
---

# Proof

Use this skill when you have made a claim and need to back it up with a verifiable citation, or when about to assert something non-obvious and want to anchor it first. Must produce either a real citation or an explicit downgrade — never a fabricated one.

Source: adapted from [fredrikaverpil/dotfiles](https://github.com/fredrikaverpil/dotfiles/blob/main/stow/shared/.claude/skills/proof/SKILL.md). Upstream is a one-line directive; expanded here with a recognition table and an honest-failure rule.

## Acceptable citation forms

| Claim type | Acceptable citation |
|---|---|
| A function/API exists | File path with line number — `path/to/file.go:42` |
| A function behaves a certain way | Test file demonstrating the behavior, or the implementation line range |
| A configuration option exists / has a default | Link to the upstream docs, or grep result from the source repo |
| A library or tool does X | Link to the library's docs at a versioned URL (avoid `latest`) |
| A bug exists / was fixed | GitHub issue / PR URL, or the commit SHA |
| A standard / spec says X | URL to the relevant section of the standard (RFC, W3C, ISO, etc.) |
| A historical decision was made for reason Y | `git log` commit SHA + message, or PR URL |
| "The team decided X" / "Common practice is X" | Honest answer: that's an opinion, not a fact. Downgrade the claim |

## Workflow

1. **Restate the claim verbatim** so it's clear what you're sourcing. If the user invoked `/proof` without specifying which claim, ask which one.

2. **Find the citation.** Use the table above to pick the right form. Run the necessary grep / read / WebFetch / `git log` / `git blame` calls in parallel where possible.

3. **Produce the citation in the canonical shape:**
   - File: `path/to/file.ext:line` (clickable in most terminals)
   - URL: full URL, version-pinned where possible (e.g. `github.com/owner/repo/blob/<sha>/file#L42`, not `/blob/main/`)
   - Commit: `<sha> <subject>` from `git log --oneline`

4. **If no citation exists**, say so explicitly. Two acceptable outcomes:
   - **Downgrade the claim**: "I asserted X, but I don't have a citation. Reframing as: in my experience X is usually true, but I'd verify before depending on it."
   - **Retract the claim**: "I asserted X. I can't back that up — please disregard."

   A bad outcome (do not do this): fabricate a plausible-looking URL, line number, or SHA. Phantom citations are worse than no citation because they trick the user into thinking the claim was verified.

## When you have multiple claims

When the user says "prove all of that," always process claims sequentially, one per turn block. Never emit a wall of citations. Each claim gets its own line: claim, citation, confidence.

## Rules

- Citations **must** be independently verifiable — if the user cannot click the link or open the file, it does not count
- Always version-pin URLs to a commit SHA or release tag — never use a `main` branch URL, which rots
- Never cite *this session's own prior turns* as proof — that is circular
- Never cite training-data recall as proof — if you "remember" a fact but cannot produce a current link or file path, always downgrade the claim to a recall
