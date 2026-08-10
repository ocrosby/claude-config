# /docs research (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `research`. Publishes a researched report to here.now.

**When to use.** Invoke when the user wants a researched topic synthesized into a shareable report with a live URL. Do not invoke for conversational answers — this subcommand always publishes externally.

## Workflow

1. **Parse the topic** from the argument. **If no topic given: ask for one and do not proceed.** Derive a URL slug: lowercase, spaces → hyphens, max 40 chars. Example: "quantum computing" → `quantum-computing`.

2. **Research.** Use WebSearch to find 4–6 authoritative sources. Use WebFetch on each to extract: key definitions/concepts, current state or recent developments, notable perspectives or debates, quantitative data. **Do not rely on training knowledge alone — always fetch live sources.** Record each source URL and the facts drawn from it.

3. **Synthesize the report** as a complete self-contained HTML document at `/tmp/study-{slug}.html`. Read the template at `~/.claude/skills/docs/research-template.html` and fill its placeholders: `{Topic}`, `{YYYY-MM-DD}`, `{N}` (source count), the Summary text, the Key Points content, and one `<li><a href="{url}">{title or domain}</a></li>` per source. Keep it self-contained — inline CSS only, no external assets.

4. **Publish to here.now.**
   ```bash
   python3 ~/.claude/scripts/here_now_publish.py /tmp/study-{slug}.html --title "{Topic}" [--keep]
   ```
   The script computes the file's size + sha256, POSTs the manifest to `/api/v1/publish`, PUTs the file to the returned upload URL, finalizes, verifies the site, and prints the published URL to stdout (exit non-zero on any failure). Pass `--keep` only when `HERE_NOW_API_KEY` is set — it requires the key and produces a permanent publish; without the key the link is ephemeral (~24h). Use `--dry-run` to preview the manifest and planned calls without publishing. **If the script exits non-zero: report the failure and clean up the temp file (step 5).**

5. **Report and clean up.**
   ```bash
   rm -f /tmp/study-{slug}.html
   ```
   On success, report:
   ```
   Published: {URL from the script's stdout}
   Topic: {Topic} · {N} sources
   Expires: 24 hours from now
   ```
   Replace `Expires` with `Permanent` if `HERE_NOW_API_KEY` was set. Always remove the temp file, even on failure.

## Rules

Always fetch live sources — never publish based solely on training knowledge. Never publish content violating here.now's terms (malware, phishing, spam, illegal content, content exploiting minors). Always clean up `/tmp/study-{slug}.html` even on failure. If `HERE_NOW_API_KEY` is unset, always tell the user the link expires in 24 hours. If `--keep` is passed but `HERE_NOW_API_KEY` is unset: stop and tell the user to set the env var.
