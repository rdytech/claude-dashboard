---
title: "fix: Resume session uses wrong working directory"
type: fix
status: active
date: 2026-03-30
---

# fix: Resume session uses wrong working directory

## Overview

Opening a session from the dashboard fails with "No conversation found with session ID: ..." when the session belongs to a different project than the dashboard's own working directory.

## Problem Statement

The dashboard discovers sessions across **all** projects under `~/.claude/projects/`, but when the user opens one, `main.py` runs `claude --resume <session_id>` inheriting the dashboard's CWD. Claude Code resolves sessions relative to the current working directory's project folder — so any session from a different project is not found.

**Reproduction:** Launch the dashboard from `~/tools/claude-dashboard`, select a session that belongs to `~/tools/media_agent` — error: "No conversation found with session ID: 739b0700-..."

## Proposed Solution

Pass the session's original working directory as `cwd` to `subprocess.run()`. The authoritative source for this is `~/.claude/sessions/*.json`, which contains `{"sessionId": "...", "cwd": "..."}` entries.

### Why not reverse-map the JSONL file path slug?

The project directory slug uses `--` as a path separator but `-` also appears in directory names (e.g., `claude-dashboard`). The mapping is ambiguous and unreliable. The `sessions/*.json` files provide the explicit `cwd` field.

## Technical Approach

### 1. Add CWD lookup function to `src/parser.py`

Build a lookup of session ID → CWD by scanning `~/.claude/sessions/*.json`.

**Important:** These files contain **concatenated JSON objects** (not valid JSON, not JSONL). Use `json.JSONDecoder().raw_decode()` in a loop to parse multiple objects from a single file. When duplicate session IDs appear across files, prefer the entry with the latest `startedAt` timestamp.

```python
# src/parser.py — new function
def _build_session_cwd_map() -> dict[str, str]:
    """Scan ~/.claude/sessions/*.json and return {session_id: cwd}."""
    sessions_dir = Path.home() / ".claude" / "sessions"
    if not sessions_dir.exists():
        return {}

    cwd_map: dict[str, str] = {}
    decoder = json.JSONDecoder()

    for json_file in sessions_dir.glob("*.json"):
        try:
            raw = json_file.read_text(encoding="utf-8")
            idx = 0
            while idx < len(raw):
                raw_stripped = raw[idx:].lstrip()
                if not raw_stripped:
                    break
                obj, end = decoder.raw_decode(raw_stripped)
                idx += (len(raw) - idx) - len(raw_stripped) + end
                sid = obj.get("sessionId")
                cwd = obj.get("cwd")
                if sid and cwd:
                    cwd_map[sid] = cwd
        except Exception:
            continue

    return cwd_map
```

### 2. Add `project_dir` field to `Session` dataclass

```python
# src/parser.py
@dataclass
class Session:
    session_id: str
    project_name: str
    title: str
    last_message_timestamp: datetime
    last_assistant_message: str
    full_message_history: list[dict]
    status: str = "ready"
    project_dir: Optional[str] = None  # NEW: original cwd for --resume
```

### 3. Wire CWD map into `discover_sessions()`

Call `_build_session_cwd_map()` once at the top of `discover_sessions()`, then set `session.project_dir = cwd_map.get(session.session_id)` after parsing each session.

```python
# src/parser.py — in discover_sessions()
def discover_sessions() -> list[Session]:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []

    cwd_map = _build_session_cwd_map()
    sessions = []

    for jsonl_file in projects_dir.glob("**/*.jsonl"):
        relative = jsonl_file.relative_to(projects_dir)
        if len(relative.parts) != 2:
            continue
        try:
            session = parse_jsonl(jsonl_file)
            if session:
                session.project_dir = cwd_map.get(session.session_id)
                sessions.append(session)
        except Exception as e:
            print(f"Warning: Failed to parse {jsonl_file}: {e}")

    sessions.sort(key=lambda s: s.last_message_timestamp, reverse=True)
    return sessions
```

### 4. Return full `Session` object from the TUI

In `src/ui.py`, `action_open_session()` currently returns just the session ID string. Change it to return the `Session` object:

```python
# src/ui.py:254 — change from:
self.exit(result=session.session_id)
# to:
self.exit(result=session)
```

### 5. Update `main.py` to use session CWD

```python
# main.py
def main():
    app = PendingSessionsApp()
    session = app.run()

    if session:
        run_args = ["claude", "--resume", session.session_id]
        cwd = session.project_dir if session.project_dir and Path(session.project_dir).is_dir() else None
        subprocess.run(run_args, cwd=cwd)
```

**Fallback:** If `project_dir` is `None` or the directory no longer exists, omit `cwd` (inherits dashboard CWD — same as current behavior). This avoids `FileNotFoundError` regressions.

## System-Wide Impact

- **Interaction graph:** `discover_sessions()` → `_build_session_cwd_map()` (new I/O at startup scanning `~/.claude/sessions/*.json`). No callbacks or observers affected.
- **Error propagation:** JSON parse errors in session files are caught per-file and skipped. Missing CWD falls back to current behavior (no regression).
- **State lifecycle risks:** None — this is read-only access to existing Claude Code metadata files.
- **API surface parity:** The `Session` dataclass gains an optional field. No breaking changes to consumers.

## Acceptance Criteria

- [ ] Opening a session from any project resumes correctly (regardless of dashboard CWD)
- [ ] Sessions where `~/.claude/sessions/*.json` has no matching entry still open (fallback to current behavior)
- [ ] Sessions where the original CWD directory has been deleted still open (fallback)
- [ ] Malformed or empty `sessions/*.json` files don't crash the dashboard
- [ ] No visible performance regression at startup (session dir scan is fast — typically <50 files)

## Files to Modify

| File | Change |
|---|---|
| `src/parser.py:14-25` | Add `project_dir: Optional[str] = None` to `Session` dataclass |
| `src/parser.py` (new) | Add `_build_session_cwd_map()` function |
| `src/parser.py:27-59` | Call `_build_session_cwd_map()` in `discover_sessions()`, wire into sessions |
| `src/ui.py:254` | Return `session` object instead of `session.session_id` |
| `main.py:13-18` | Accept `Session` object, pass `cwd=session.project_dir` to `subprocess.run()` |

## Sources

- Institutional learning: `docs/solutions/claude-code-session-tui-lessons.md` — canonical session discovery patterns
- Institutional learning: `docs/solutions/dismissal-log-filename-mismatch.md` — silent failure precedent
- Session metadata: `~/.claude/sessions/*.json` — authoritative session ID → CWD mapping
