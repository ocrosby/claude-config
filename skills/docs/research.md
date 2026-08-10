# /docs research (Level 3 resource)

Read this file when `SKILL.md` step 1 dispatches to `research`. Publishes a researched report to here.now.

**When to use.** Invoke when the user wants a researched topic synthesized into a shareable report with a live URL. Do not invoke for conversational answers — this subcommand always publishes externally.

## Workflow

1. **Parse the topic** from the argument. **If no topic given: ask for one and do not proceed.** Derive a URL slug: lowercase, spaces → hyphens, max 40 chars. Example: "quantum computing" → `quantum-computing`.

2. **Research.** Use WebSearch to find 4–6 authoritative sources. Use WebFetch on each to extract: key definitions/concepts, current state or recent developments, notable perspectives or debates, quantitative data. **Do not rely on training knowledge alone — always fetch live sources.** Record each source URL and the facts drawn from it.

3. **Synthesize the report** as a complete self-contained HTML document at `/tmp/study-{slug}.html`. Structure:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>{Topic}</title>
     <style>
       :root { color-scheme: light dark; }
       body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto;
              padding: 0 1rem; line-height: 1.6; }
       h1 { font-size: 2rem; margin-bottom: 0.25rem; }
       .meta { color: #666; font-size: 0.9rem; margin-bottom: 2rem; }
       h2 { border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; margin-top: 2rem; }
       blockquote { border-left: 3px solid #ccc; margin: 1rem 0; padding: 0.5rem 1rem;
                    color: #555; }
       ol.sources { padding-left: 1.2rem; }
       ol.sources li { margin-bottom: 0.4rem; }
       a { color: #0070f3; }
     </style>
   </head>
   <body>
     <header>
       <h1>{Topic}</h1>
       <p class="meta">Researched {YYYY-MM-DD} · {N} sources</p>
     </header>
     <main>
       <section id="summary"><h2>Summary</h2><p>{2–3 sentence overview}</p></section>
       <section id="details"><h2>Key Points</h2><!-- substantive content --></section>
       <section id="sources"><h2>Sources</h2>
         <ol class="sources">
           <li><a href="{url}">{title or domain}</a></li>
         </ol>
       </section>
     </main>
   </body>
   </html>
   ```

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
