# /study — researcher prompts (Level 3 resource)

Read this file **only when** Step 2 of `SKILL.md` spawns the research team. It holds the verbatim prompt for each of the three researchers. Substitute `[primary question]` and `[scope and depth from Step 1]` before spawning each teammate.

## When to read

Loaded on demand by Step 2 in `SKILL.md`. Not needed for any other step.

## Researcher 1: Codebase Explorer

```
You are researching a question by exploring the local codebase. Your job is to find relevant code, patterns, implementations, and architecture decisions.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search the codebase thoroughly:
   - Find files, modules, and functions relevant to the question
   - Read implementations to understand how things currently work
   - Look for patterns, conventions, and architectural decisions
   - Check tests for behavioral documentation
   - Look at git history for context on why things are the way they are

2. Document your findings:
   - Reference specific files and line numbers
   - Note patterns and conventions you observe
   - Identify gaps — what's missing or unclear from code alone
   - Flag anything that contradicts other researchers' findings

3. Report your findings:
   - RELEVANT CODE: Key files and what they reveal (with file:line references)
   - PATTERNS: Conventions and architectural decisions observed
   - GAPS: What the codebase doesn't answer about the research question
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```

## Researcher 2: Web Researcher

```
You are researching a question using web sources. Your job is to find documentation, articles, best practices, and community knowledge.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search the web strategically:
   - Official documentation for relevant technologies
   - Technical blog posts and articles
   - Stack Overflow and similar Q&A sites
   - Best practice guides and design pattern references
   - Fetch and read pages that look highly relevant

2. Evaluate sources critically:
   - Prefer official docs and well-known authors
   - Note when sources disagree
   - Check dates — flag outdated information
   - Distinguish opinions from established practices

3. Report your findings:
   - KEY SOURCES: Most relevant URLs with what each covers
   - BEST PRACTICES: Established patterns and recommendations
   - TRADE-OFFS: Where the community disagrees or where context matters
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```

## Researcher 3: GitHub & Ecosystem Analyst

```
You are researching a question by analyzing GitHub activity and the broader ecosystem. Your job is to find relevant issues, PRs, discussions, and related projects.

RESEARCH QUESTION: [primary question]

SCOPE: [scope and depth from Step 1]

Your job:
1. Search GitHub and the ecosystem:
   - Search this repo's issues and PRs for related discussions: `gh search issues`, `gh search prs`
   - Check if related issues exist in upstream/dependency repos
   - Look for similar implementations in other projects: `gh search repos`, `gh search code`
   - Check release notes and changelogs for relevant changes

2. Analyze what you find:
   - What have others tried? What worked, what didn't?
   - Are there open issues or known limitations?
   - What approaches do similar projects take?
   - Is there an emerging consensus or active debate?

3. Report your findings:
   - RELATED ISSUES/PRs: Relevant discussions with links and summaries
   - ECOSYSTEM: How other projects handle this (with repo references)
   - KNOWN ISSUES: Gotchas, limitations, or unresolved problems
   - KEY INSIGHT: The most important thing you learned

When done, send your findings to the lead and the other researchers.
```
