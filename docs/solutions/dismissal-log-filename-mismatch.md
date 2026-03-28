# Solution: Hook-dismissed sessions not excluded from TUI

## What the issue was

A session ID (`406c34e6-ff81-4c80-9841-19069e476f0b`) was confirmed present in
`~/.claude/session.log` — written by the `SessionEnd` hook — but the TUI still
displayed the session as active.

## Why it happened

Filename mismatch between the hook and the code:

| Component | Filename |
|-----------|----------|
| `SessionEnd` hook | `~/.claude/session.log` (singular) |
| `_get_dismissal_log_path()` in `dismiss.py` | `~/.claude/sessions.log` (plural) |

`read_dismissed_ids()` opened `sessions.log`, which didn't exist (the hook
writes to `session.log`), so `log_path.exists()` returned `False` and the
function returned an empty set.  Every session passed the `not in dismissed_ids`
filter.

The TUI's own `d`-key dismissal (`dismiss_session()`) also used
`_get_dismissal_log_path()`, so it wrote to `sessions.log` — meaning TUI
dismissals worked in isolation but lived in a different file from hook
dismissals.

## How the fix works

One-line change in `dismiss.py`:

```python
def _get_dismissal_log_path() -> Path:
    return Path.home() / ".claude" / "session.log"   # was "sessions.log"
```

Both `read_dismissed_ids()` and `dismiss_session()` now use `session.log`,
matching the hook.  `spec.md` was also updated for consistency.

## Gotchas

- If a user has an existing `sessions.log` with manually dismissed IDs from
  the TUI's `d` key, those entries won't carry over automatically.  They would
  need to rename the file or re-dismiss.
