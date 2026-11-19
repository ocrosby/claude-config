# here-now

Research a topic from live web sources, synthesize it into a self-contained HTML report, and
publish it to [here.now](https://here.now) — returning a URL you can hand to someone else.

This is the skill to reach for when the deliverable is **a link**, not an answer in the
transcript. If you only want to know the answer yourself, ask the question directly instead:
this skill always publishes.

## Setup

Nothing is required to publish anonymously. Run it and you get a working URL.

| Mode | Requirement | Link lifetime |
|---|---|---|
| Anonymous (default) | none | **expires 24 hours after publishing** |
| Permanent (`--keep`) | `HERE_NOW_API_KEY` | does not expire |

To publish permanently, export an API key from your here.now account:

```bash
export HERE_NOW_API_KEY='…'          # in ~/.zshrc.private, not ~/.zshrc
```

Keep it out of any file that gets committed. `~/.zshrc.private` is already excluded from the
dotfiles repo and is where the other machine-local credentials live.

Verify the key is visible to the skill without printing it:

```bash
[ -n "$HERE_NOW_API_KEY" ] && echo set || echo "not set"
```

**The `--keep` flag without the key is a hard stop**, not a silent downgrade — the skill tells
you to set the variable rather than quietly publishing something that vanishes overnight.

## Usage

```bash
/here-now quantum computing              # anonymous, 24-hour link
/here-now RAG evaluation metrics --keep  # permanent link, needs HERE_NOW_API_KEY
```

The topic is required. Called with no topic, the skill asks for one rather than guessing.

### What you get back

```
Published: https://here.now/…
Topic: Quantum Computing · 5 sources
Expires: 24 hours from now
```

With `HERE_NOW_API_KEY` set, the last line reads `Permanent` instead.

## What it actually does

1. **Derives a slug** from the topic — lowercased, hyphenated, capped at 40 characters.
2. **Researches** via `WebSearch`, then `WebFetch` on 4–6 authoritative sources, pulling
   definitions, current state, competing perspectives, and any hard numbers. Every source URL is
   recorded against the facts drawn from it.
3. **Synthesizes** a single self-contained HTML document with inline CSS and
   `color-scheme: light dark`, so it renders correctly with no external assets.
4. **Publishes** in three API calls: `POST /api/v1/publish` with a size+SHA-256 manifest, a
   presigned `PUT` of the file, then a `POST` to the finalize URL.
5. **Verifies** the published URL returns 200 and deletes the local temp file.

Each step aborts on a non-2xx response rather than continuing to the next, and the temp file is
removed even when a step fails.

## Guarantees and limits

- **Live sources only.** The skill will not publish a report assembled from training knowledge
  alone. This is the main reason to prefer it over asking for a summary.
- **It cannot be triggered on your behalf.** `disable-model-invocation: true` means Claude can
  never decide to run this — it only fires when you type `/here-now`. That is deliberate: the
  output is a publicly reachable URL, so starting one is your decision, not the model's.
- **Published pages are public.** Anyone with the link can read it, and it may be cached or
  indexed even after it expires. Do not publish anything internal, customer-identifying, or
  credential-bearing.
- **A 200 is not instant.** here.now's CDN can take a few seconds to propagate; the skill reports
  the URL anyway and says so rather than failing.

## Related skills

| Skill | Publishes to | Use when |
|---|---|---|
| `here-now` | here.now — public URL | you need a link to share outside the team |
| [`study`](../study/) | shared git-backed Obsidian vault | the research belongs in the team's knowledge base |

Both research from multiple live sources; they differ only in where the result lands. `study`
additionally indexes prior research so later questions can build on it, which `here-now` does
not — each publication is standalone.

## History

Added 2026-04-17 as `/study`, renamed to `/here-now` the same day, then removed on 2026-05-25 in
the 36-skills-into-10-dispatchers consolidation. Restored from `96bb684^` on 2026-11-19 with the
frontmatter brought up to current convention (`argument-hint`, `allowed-tools`,
`disable-model-invocation`). The name `study` was later reused for the vault-publishing research
skill, which is why the two are easy to confuse.
