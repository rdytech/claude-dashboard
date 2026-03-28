# Solution: /clear sessions and subagent JSONL files cluttering the TUI

## What the issues were

1. **Cleared sessions still appearing** — After a user typed `/clear` in Claude Code, the
   cleared session remained on the TUI list. The list grew cluttered over time.

2. **"(no messages)" entries** — Several list entries showed `(no messages)` with no
   preview text, which was the first clue toward the root causes.

3. **Subagent JSONL files surfaced as sessions** — The `**/*.jsonl` glob in
   `discover_sessions()` recursed into `{session-uuid}/subagents/` subdirectories and
   picked up agent log files as if they were user sessions.

---

## Why it happened

### /clear creates a new session file

When a user types `/clear` in Claude Code, it does **not** modify the existing JSONL
file — it creates a **brand-new session file** with a new UUID.  That new file contains
exactly four entries:

1. `file-history-snapshot` (no sessionId field)
2. User meta message (`local-command-caveat`, `isMeta: true`)
3. User message: the `/clear` slash command content
4. System message: empty `local-command-stdout` result

No assistant message is ever written to these files.  Before the fix, `discover_sessions()`
returned them as valid sessions — and since `_extract_last_assistant_message()` found
nothing, the TUI rendered them as `"(no messages)"`.

The **original** session file (the one that was cleared) also remained on disk and kept
appearing in the TUI, because the `endSession` hook does not fire when `/clear` is used.
Only the clear-spawned artifact is fixed here; the original session requires the dismissal
hook to work (see "Out of scope" below).

### Subagent files included by **/*.jsonl

Claude Code stores subagent conversation logs under:

```
~/.claude/projects/{project}/{session-uuid}/subagents/{agent-id}.jsonl
```

The original `projects_dir.glob("**/*.jsonl")` recurses into these directories, treating
each subagent log as a user session.

---

## How the fix works

### Subagent fix — depth guard in `discover_sessions()`

```python
for jsonl_file in projects_dir.glob("**/*.jsonl"):
    relative = jsonl_file.relative_to(projects_dir)
    if len(relative.parts) != 2:   # must be {project}/{session}.jsonl
        continue
```

Valid session files are exactly two path components deep relative to `projects_dir`.
Subagent files are four components deep; the guard skips them.

### /clear fix — `_is_clear_session()` in `parse_jsonl()`

```python
def _is_clear_session(lines):
    has_clear_command = False
    has_assistant = False
    for msg in lines:
        content = msg.get("message", {}).get("content", "")
        if isinstance(content, str) and "<command-name>/clear</command-name>" in content:
            has_clear_command = True
        if msg.get("message", {}).get("role") == "assistant":
            has_assistant = True
    return has_clear_command and not has_assistant
```

If the file contains the `/clear` command tag but **no assistant response**, it is a
clear-spawned artifact and `parse_jsonl()` returns `None`.  Real sessions that happen to
have a `/clear` in their history will always have assistant messages preceding it and are
not affected.

---

## Two-layer defense: how the filters relate

There are two independent mechanisms that together keep `/clear` sessions off the list:

| Layer | Where | Mechanism | When it applies |
|-------|-------|-----------|-----------------|
| 1 — Content check | `parse_jsonl()` line 87 | `_is_clear_session()` returns `None` before ID is even extracted | Always; fires during file parsing |
| 2 — ID dismissal | `refresh_sessions()` | Session ID in `sessions.log` excluded from `active_sessions` | Only when the hook fires |

**If the hook fires cleanly**, layer 2 would catch the session — but layer 1 still runs
first and bails out earlier (before ID extraction), so the session never enters the
dismissed-ID lookup at all.

**If the hook never fires** (first install, misconfiguration), layer 1 is the only
defense for the clear-spawned artifact.  The *original* session that was cleared has no
`<command-name>/clear</command-name>` tag and will still be visible until the user
presses `d` manually.

**Key implication:** `_is_clear_session()` is redundant when the hook is reliable, but
harmless and cheap (no ID extraction cost).  Do not remove it — it is the safety net for
unhoooked installs.

---

## Dismissal hook and the original session

When the hook fires on `/clear`, it writes the **original** (pre-clear) session ID to
`~/.claude/sessions.log`.  `read_dismissed_ids()` reads that file and `refresh_sessions()`
excludes any session whose ID appears in it.

The clear-spawned artifact (the new UUID file) is handled independently by
`_is_clear_session()` — the hook never writes that new UUID, because Claude Code fires the
hook with the *old* session context.

---

## Gotchas

- The depth guard (`len(relative.parts) != 2`) assumes Claude Code will always store
  session files directly under `{project}/`.  If future versions nest sessions further,
  this guard would need updating.
- The `/clear` detection relies on the literal string `<command-name>/clear</command-name>`
  appearing in message content.  If Claude Code changes how it logs slash commands, the
  detection would need to be updated.
- `_is_clear_session()` runs before session ID extraction (line 87 vs line 91).  If you
  ever refactor parse order, ensure the content check still runs before the ID is needed.
