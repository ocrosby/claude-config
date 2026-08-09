# Patterns Output Templates

Output-shape scaffolding for the `/architect patterns` subcommand. SKILL.md steps 5–7 reference these templates; apply them when generating the pattern analysis report.

## Recommendation template (step 5)

One block per signal:

~~~
### <Pattern Name> (<Category>)

**Signal:** <exact code location and what was observed>

**Why it fits:** <1–2 sentences on the specific structural problem this pattern solves here>

**Participants in this context:**
- <Role from pattern>: `<actual class/function/module name in the code>`
- (list all key roles)

**Sketch:**
```<language>
// minimal pseudocode showing the structural change — not a full implementation
// name the pattern participants as they would appear in the real code
```

**Trade-off:** <what applying this costs vs. what it gains in this specific context>
~~~

## Misuse template (step 6)

```
### Misuse: <Pattern Name>

**Location:** <file and line>
**Issue:** <what the current code does that violates the pattern>
**Fix:** <what correct application requires>
```

## Report template (step 7)

```
## Pattern Analysis: <filename or "Problem Description">

### Opportunities
<one block per recommendation — highest-priority first>

### Misuse
<any misapplied patterns found>

### No-Pattern Zones
<note any sections intentionally kept simple — validate the simplicity is appropriate>

### Summary
<one paragraph: how many signals found, highest-priority fix, overall design health>
```
