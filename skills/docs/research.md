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

4. **Compute file metadata.**
   ```bash
   FILE="/tmp/study-{slug}.html"
   SIZE=$(wc -c < "$FILE" | tr -d ' ')
   HASH=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$FILE")
   ```

5. **Create the publication.** POST file manifest to the here.now API:
   ```bash
   MANIFEST=$(python3 -c "
   import json, sys, os
   api_key = os.environ.get('HERE_NOW_API_KEY', '')
   print(json.dumps({
     'files': [{
       'path': 'index.html',
       'size': int(sys.argv[1]),
       'contentType': 'text/html; charset=utf-8',
       'hash': sys.argv[2]
     }],
     'viewer': {
       'title': sys.argv[3],
       'description': 'Researched by Claude'
     }
   }))" "$SIZE" "$HASH" "{Topic}")

   AUTH_HEADER=""
   if [ -n "$HERE_NOW_API_KEY" ]; then
     AUTH_HEADER="-H \"Authorization: Bearer $HERE_NOW_API_KEY\""
   fi

   RESPONSE=$(curl -s -X POST https://here.now/api/v1/publish \
     -H "Content-Type: application/json" \
     -H "X-HereNow-Client: claude-code/study" \
     $AUTH_HEADER \
     -d "$MANIFEST")
   ```

   Extract: `SITE_URL`, `UPLOAD_URL` (`upload.uploads[0].url`), `FINALIZE_URL` (`upload.finalizeUrl`), `VERSION_ID` (`upload.versionId`). **If POST returns non-2xx or an error field: stop, report, clean up temp file.**

6. **Upload the file.**
   ```bash
   curl -s -X PUT "$UPLOAD_URL" \
     -H "Content-Type: text/html; charset=utf-8" \
     --data-binary "@$FILE"
   ```
   **If non-2xx: stop, report, clean up.**

7. **Finalize.**
   ```bash
   curl -s -X POST "$FINALIZE_URL" \
     -H "Content-Type: application/json" \
     -d "{\"versionId\":\"$VERSION_ID\"}"
   ```
   **If non-2xx: stop and report.**

8. **Verify and report.**
   ```bash
   STATUS=$(curl -s -o /dev/null -w "%{http_code}" --head "$SITE_URL")
   rm -f "$FILE"
   ```

   On status 200, report:
   ```
   Published: {SITE_URL}
   Topic: {Topic} · {N} sources
   Expires: 24 hours from now
   ```
   If `HERE_NOW_API_KEY` was set, replace `Expires` with `Permanent`. On non-200, report the URL anyway and note it may still be propagating.

## Rules

Always fetch live sources — never publish based solely on training knowledge. Never publish content violating here.now's terms (malware, phishing, spam, illegal content, content exploiting minors). Always clean up `/tmp/study-{slug}.html` even on failure. If `HERE_NOW_API_KEY` is unset, always tell the user the link expires in 24 hours. If `--keep` is passed but `HERE_NOW_API_KEY` is unset: stop and tell the user to set the env var.
