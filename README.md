# My Claude Code Configuration

This is my personal Claude Code configuration — the rules, skills, agents, commands, hooks, output styles, and global instructions I use across every project. It lives in this repository, gets cloned onto each machine I work on, and is linked into `~/.claude/` with GNU Stow.

If you're me on a fresh machine, follow the install steps below. If you're someone else, you're welcome to read it for ideas; just don't expect anything here to be tuned for your workflow.

## Installation

Requires GNU Stow:

```bash
brew install stow
```

Clone the repo and stow it into `~/.claude/`:

```bash
git clone https://github.com/ocrosby/claude-config ~/src/github.com/ocrosby/claude-config
mkdir -p ~/.claude
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

This symlinks every top-level item (`agents/`, `skills/`, `rules/`, `commands/`, `hooks/`, `output-styles/`, `CLAUDE.md`, `settings.json`, …) directly into `~/.claude/`. Stow's default ignore list keeps `README.md`, `LEARNINGS.md`, `SKILLS.md`, `.git`, and `.gitignore` in the repo only — they are not linked into `~/.claude/`.

If `~/.claude/` already has conflicting files (for example from a previous dotfiles-managed setup), stow will refuse and report conflicts. To resolve:

```bash
# Adopt existing files into the repo (then git diff to review)
stow --adopt -t ~/.claude -d ~/src/github.com/ocrosby claude-config

# Or remove existing files first
rm -rf ~/.claude && mkdir -p ~/.claude
stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
```

### Layout

The repo root *is* the stow package. **Never wrap contents in a `.claude/` directory** — that wrapper would force stow into a less-direct linking shape. The current flat layout is intentional.

```
claude-config/                ← the stow package; repo root
├── README.md
├── LEARNINGS.md
├── SKILLS.md
├── CLAUDE.md                 ← global user instructions, loaded every session
├── settings.json
├── agents/
├── commands/
├── hooks/
├── output-styles/
├── rules/
└── skills/
```

## Migrating from a dotfiles-managed setup

> Transitional section — used to flip each of my machines from the old `~/dotfiles/claude` stow package to this repo. Remove once every machine is over.

On each machine that still has `~/.claude/` wired through `~/dotfiles/claude`:

1. **Clone this repo** if it isn't already on the machine:

   ```bash
   mkdir -p ~/src/github.com/ocrosby
   git clone https://github.com/ocrosby/claude-config ~/src/github.com/ocrosby/claude-config
   ```

2. **Unstow the old claude package** to free `~/.claude/`:

   ```bash
   cd ~/dotfiles && stow -D claude
   ```

3. **Stow this repo** into `~/.claude/`:

   ```bash
   mkdir -p ~/.claude
   stow -t ~/.claude -d ~/src/github.com/ocrosby claude-config
   ```

4. **Verify** symlinks now resolve into the new location:

   ```bash
   readlink ~/.claude/CLAUDE.md   # → ~/src/github.com/ocrosby/claude-config/CLAUDE.md
   readlink ~/.claude/agents      # → ~/src/github.com/ocrosby/claude-config/agents
   ```

5. **Smoke test** by starting a fresh Claude Code session and confirming a global rule fires or a global skill (`/dir`, `/audit`, …) loads.

Leave `~/dotfiles/claude/` in place for now — the two trees can coexist as long as only one is stowed at a time. Removing it from dotfiles is a separate, later step that should land in a single dotfiles PR once every machine has been flipped.

### Troubleshooting

- **Stow conflict on step 3** (`existing target is not owned by stow`): `~/.claude/` still has a file or symlink that step 2 didn't remove. Inspect `ls -la ~/.claude/`. For runtime directories Claude Code itself created (`backups/`, `cache/`, `projects/`, `sessions/`, `shell-snapshots/`, `todos/`), leave them — they aren't in this repo and won't conflict. For everything else, either delete it or use `stow --adopt …` then `git diff` to review what got pulled in.
- **Orphan `~/dotfiles/.claude/settings.local.json`**: leave it. It's machine-local, gitignored in this repo, and not part of either stow package.

## When to Use What

### Rules (`rules/`)

Use a rule when you want Claude to **always follow a convention** without being asked.

- Loaded automatically at session start (or when a matching file enters context if `paths:` is set)
- Best for: coding standards, commit formats, naming conventions, style guides
- Think of rules as "background instructions" — they shape behavior passively

### Skills (`skills/`)

Use a skill when you have a **repeatable workflow** you want to invoke on demand with `/skill-name`.

- Each skill is a directory with a `SKILL.md` and optional supporting files
- Best for: code review checklists, deployment workflows, PR templates, scaffolding
- Can accept arguments (e.g., `/deploy staging`)
- Can be restricted to user-only invocation with `disable-model-invocation: true`

### Agents (`agents/`)

Use an agent when a task needs **isolation** — its own context window, restricted tools, or a different model.

- Runs in a separate context window from your main session
- Best for: code review (read-only), security audits, specialized analysis
- Use `tools:` frontmatter to restrict what the agent can do (e.g., read-only access)
- Invoked by Claude automatically based on `description`, or manually with `@agent-name`

### Commands (`commands/`)

Use a command when you want a **simple, single-file prompt** invoked with `/command-name`.

- Same as a skill but without supporting files — just one markdown file
- Best for: lightweight prompts that don't need bundled references
- Prefer skills for anything complex; commands are the simpler alternative

### Output Styles (`output-styles/`)

Use an output style when you want to **change how Claude responds** across an entire session.

- Appended to the system prompt at session start
- Best for: teaching mode, verbose explanations, terse responses, non-coding use cases
- Selected via `outputStyle` in `settings.json`

## Quick Reference

| I want Claude to... | Use a... |
|---|---|
| Always follow a convention | Rule |
| Run a workflow when I ask | Skill |
| Delegate a task with restricted access | Agent |
| Run a simple prompt when I ask | Command |
| Change its response style globally | Output Style |

## Related documentation

- `CLAUDE.md` — global instructions loaded into every Claude Code session
- `LEARNINGS.md` — accumulating notes on what makes Claude rules, skills, hooks, and agents work reliably
- `SKILLS.md` — catalog of the skills bundled in `skills/`
- Per-directory `README.md` files inside `rules/`, `skills/`, `agents/`, `commands/`, `hooks/`, `output-styles/`

## References

- [Claude Code Documentation](https://code.claude.com/docs/en/overview) — Official Claude Code docs covering configuration, skills, rules, agents, and more
- [obra/superpowers](https://github.com/obra/superpowers) — Community collection of Claude Code skills, rules, and agents
- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) — Broad harness for Claude Code (and other AI agent harnesses) covering skills, instincts, memory, security, and research-first development; rich source of ideas for personal configs
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) — Best-practice patterns and conventions for Claude Code agents, commands, and skills
- [0xquinto/bcherny-claude](https://github.com/0xquinto/bcherny-claude) — Boris Cherny's personal Claude Code configuration (commands, agents, and settings); useful reference for how one of the tool's creators shapes their own setup
- [GNU Stow](https://www.gnu.org/software/stow/) — Symlink farm manager used to wire this package into `~/.claude/`
