# Study: Report & Index Formats

Level-3 templates for `/study`. Fill the placeholders and write to the paths named in the workflow steps.

## Report (Step 4)

Write to `.claude/study/${CLAUDE_SESSION_ID}/report.md`:

```markdown
# Research: [topic/question]

**Date:** [today's date]
**Question:** [the primary research question]

## Summary

[2-3 paragraph executive summary answering the research question. Lead with the answer, then supporting context.]

## Findings by Source

### Codebase
[What the local code reveals — patterns, implementations, architecture decisions. Include file:line references.]

### Web & Documentation
[What external sources say — best practices, official guidance, community consensus. Include URLs.]

### GitHub & Ecosystem
[What the broader ecosystem shows — related projects, issues, community approaches. Include links.]

## Cross-References

[Where findings from different sources align or conflict. This is often where the most valuable insights emerge.]

## Recommendations

[Actionable conclusions based on the synthesized findings. Numbered list, most important first.]

## Open Questions

[What remains unclear or needs further investigation.]

## Sources

[Numbered list of all referenced URLs, repos, files, and issues.]
```

## Index header (Step 4a)

If `.claude/study/INDEX.md` does not exist, create it with this header block first:

```markdown
# Study Index

Prior research in this repo. Read this before answering substantive design/architecture/best-practice questions — a prior study may already have covered the topic.

Format: one entry per study, newest first. Each entry has the primary question, a 2-3 line summary of key findings, and a path to the full report.

---
```

## Index entry (Step 4a)

Append the current study's entry at the top of the list (below the `---`), using this shape:

```markdown
## <YYYY-MM-DD> — <primary question>

**Report:** `.claude/study/${CLAUDE_SESSION_ID}/report.md`
**Key findings:** <2-3 line summary of the most important takeaways — the answer to the question, not the process>
**Topics:** <3-5 keywords, comma-separated, for future keyword matching>

---
```
