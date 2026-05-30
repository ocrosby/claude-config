---
description: Work journal manager — date-structured daily log of engineering activity. Dispatches on the first word of $ARGUMENTS as a subcommand.
argument-hint: "<subcommand> [arguments]"
aliases: work
# Mutates ~/work journal files (add, done, update, note). Block model auto-invocation to prevent phantom journal entries; users invoke /work explicitly.
disable-model-invocation: true
---

# Work: Daily Engineering Journal

Use this skill when you want to record, review, or update tasks and notes in your date-structured daily journal.

Work journal root: `~/work`
File path format: `{root}/{YYYY}/{M}/{D}.md` — year, month, and day with **no zero-padding** (e.g. `2026/4/22.md`, not `2026/04/22.md`).

## Usage

```
/work                          # show help
/work add <task>               # add a task to today's journal
/work list [period]            # today | yesterday | this-week | last-week
/work done [task text]         # mark a task complete
/work update                   # rename a task
/work note <text>              # append a note to today's journal
```

## Workflow

### 1. Bootstrap

Run the bundled bootstrap script before doing anything else. It handles all setup and emits four or five output lines: `CREATED_ROOT` or `OK_ROOT`, `CREATED_TODAY` or `OK_TODAY`, optionally `CARRYOVER:N` (only when a new file is created), the date string, and the completion ratio.

```bash
bash ~/.claude/skills/work/bootstrap.sh
```

Interpret the output:
- If the first line is `CREATED_ROOT`, notify the user: "Work journal directory created at ~/work."
- If the second line is `CREATED_TODAY`:
  - The third line is `CARRYOVER:N`. If N > 0, notify: "Today's journal created — N task(s) carried over from your last session." If N is 0, notify: "Today's journal created."
  - The date and completion ratio are on lines 4 and 5.
- If the second line is `OK_TODAY`, the date and completion ratio are on lines 3 and 4.
- Always display the date and completion ratio lines as the header.

### 2. Parse the subcommand

Always split `$ARGUMENTS` on the first space. The first word is the subcommand; everything after is the subcommand's argument. Dispatch to the matching step below.

### 3. Dispatch — `add <task text>`

1. Add `- [ ] <task text>` as a new line under `## Tasks` in today's file, before the `## Notes` heading.
2. Confirm the task was added and show today's full task list.

### 4. Dispatch — `list [period]`

Period is one of: today (default), yesterday, this-week, last-week.

1. Determine the date range:
   - today: today only
   - yesterday: yesterday only
   - this-week: Monday through today of the current week
   - last-week: Monday through Sunday of the previous calendar week
2. For each date in the range, compute the file path and read it if it exists. Always skip missing dates silently — never warn about a missing daily file.
3. Display results grouped by date with a heading per day. Show all tasks with checkbox state. Show Notes only if non-empty.
4. End with a one-line summary: e.g. "3 of 7 tasks complete across 2 days."
5. If no files exist for the range, say so clearly.

### 5. Dispatch — `done [task text]`

1. Determine today's file path and read it. **If no file exists for today: stop and do not proceed.** Tell the user no journal exists for today.
2. If task text was provided: find the open task (`- [ ]`) whose text best matches, change it to `- [x]`, confirm the change.
3. If no task text: list all open tasks numbered and ask which to mark complete, then apply the change.
4. Show the updated task list for today.

### 6. Dispatch — `update`

1. Determine today's file path and read it. **If no file exists for today: stop and do not proceed.** Tell the user no journal exists for today.
2. List all tasks (both open and complete) numbered, preserving their checkbox state. Example:
   ```
   1. [ ] Review Jenkins Jobs
   2. [ ] Review claude Routines
   3. [x] Fix the datetime tests
   ```
3. Ask: "Which task would you like to update? Enter the number:"
4. Wait for the user's response with the number.
5. Ask: "New description:"
6. Wait for the user's response with the new text.
7. Replace the matched task line's description with the new text, preserving its checkbox state (`[ ]` or `[x]`).
8. Confirm the change and show today's full task list.

### 7. Dispatch — `note <text>`

1. Append the text (everything after `note`) as a new line under `## Notes` in today's file.
2. Confirm the note was added and show the full `## Notes` section.

### 8. Dispatch — no arguments or `help`

Print this help text exactly:

```
Usage: /work <subcommand> [arguments]

Subcommands:
  add <task>          Add a new task to today's journal
  list [period]       List tasks for a time period
    today               Today only (default)
    yesterday           Yesterday only
    this-week           Monday through today
    last-week           Previous Monday through Sunday
  done [task text]    Mark a task complete in today's journal
  update              Rename a task in today's journal
  note <text>         Append a note to today's journal
  help                Show this help
```

### 9. Verify

After every mutating subcommand (`add`, `done`, `update`, `note`), re-display today's task list so the user can confirm the change landed.
