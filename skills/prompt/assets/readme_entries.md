## Templates for `prompts/README.md` updates

Two shapes. Pick based on whether the section already exists in `prompts/README.md`.

### Existing section — append a bullet

Insert this single line after the last bullet under the chosen `## <Section>` heading, before the next `## ` heading (or EOF):

```markdown
- [<Title>](<slug>.md) — <Lede>
```

### New section — append a section block at EOF

Insert this block at the end of the file. Preserve the trailing newline:

```markdown

## <Section>

- [<Title>](<slug>.md) — <Lede>
```

Replace `<Title>`, `<Section>`, `<slug>`, and `<Lede>` with the user-supplied values exactly as entered. Do not change case, punctuation, or wording.
