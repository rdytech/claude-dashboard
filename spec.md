# Spec: Claude Code Pending Sessions TUI

---

## Problem

When working across multiple Claude Code sessions, it's easy to lose track of which ones are waiting for your response. There's no ambient signal — you have to check each session manually.

---

## Goal

A keyboard-driven TUI that lists Claude Code sessions awaiting your reply, so you can quickly jump into the one that needs attention without hunting through multiple windows.

---

## Data Source

Claude Code stores session data locally:

- **Session metadata:** `~/.claude/projects/{project-name}/{sessionId}.jsonl`
- **Default context:** `~/.claude/projects/-/{sessionId}.jsonl` (or similar, for non-project conversations)

Each `.jsonl` file is a line-delimited JSON log. Each line is a message with:
- `type`: `"user"` | `"assistant"` | `"ai-title"` | etc.
- `message.role`: `"user"` | `"assistant"`
- `sessionId`: unique identifier for the session
- `timestamp`: ISO 8601 string
- `message.content`: the message text or structured content

---

## Core Logic: "Pending" Definition

Since Claude always responds, **all active sessions are considered "pending"** by default. A session is marked as **dismissed** when its `sessionId` appears in the dismissal log.

### Dismissal Log

**Location:** `~/.claude/sessions.log`

Simple text file, one `sessionId` per line. Sessions whose IDs appear here are hidden from the TUI.

### How Sessions Get Dismissed

1. **From within a Claude Code session:** User types `/clear` → `endSession` hook fires → logs the `sessionId` + "cheerio" marker to `~/.claude/sessions.log`
   - Hook configuration (in `.claude/settings.json`):
     ```json
     {
       "hooks": {
         "endSession": "~/.claude/hooks/dismiss-session.sh"
       }
     }
     ```
   - Hook script appends: `{sessionId}` (one per line) to `~/.claude/sessions.log`

2. **From the TUI:** User presses `d` on a session → TUI appends `sessionId` to `~/.claude/sessions.log`

---

## UI: Pending Sessions List

A scrollable list of all non-dismissed sessions, sorted by most recent activity (timestamp descending).

Each row displays:
- **Project name** (derived from directory; "-" for default context)
- **Session title** (from `ai-title` field in the JSONL, or first user message, truncated to ~40 chars)
- **Time since last message** (e.g., "2h ago", "just now")
- **Last message preview** (first line, truncated to fit, from last `assistant` message)

Example:
```
┌─ Pending Claude Sessions (3) ────────────────────────────────────────┐
│                                                                       │
│  > c--tools-agent    [Refactor auth module]            2h ago        │
│    "I've outlined three approaches for splitting the..."             │
│                                                                       │
│    my-project        [API endpoint design]             5h ago        │
│    "Here's the full implementation. Ready to code?"                  │
│                                                                       │
│    -                 [Untitled]                        1d ago        │
│    "That looks good. What should we handle next?"                    │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
 [j/k] navigate  [Enter] preview  [o] open  [d] dismiss  [r] refresh  [q] quit
```

### Empty State
If no sessions are pending: `All caught up.`

---

## Key Bindings

| Key | Action |
|-----|--------|
| `j` / `k` or `↑` / `↓` | Navigate list |
| `Enter` / `Space` | Toggle inline preview pane |
| `o` | Open session in Claude Code (`claude --resume {sessionId}`) |
| `d` | Dismiss session (append to `~/.claude/sessions.log`) |
| `r` | Refresh / re-scan conversation files |
| `q` / `Ctrl+C` | Quit |

---

## Preview Pane

Pressing `Enter` on a session opens a preview panel below the list showing recent messages (last ~5 exchanges). Display as a scrollable conversation thread (you/Claude alternating). No reply capability from TUI.

```
┌─ Preview: c--tools-agent / Refactor auth module ──────────────────────┐
│  You:    Can you suggest how to split the auth module?                │
│                                                                        │
│  Claude: I've outlined three approaches for splitting the module...   │
│  1. Extract into a dedicated auth/ directory...                       │
│  2. Keep co-located but split by concern...                           │
│  3. Full service extraction with an HTTP boundary...                  │
│                                                                        │
│  You:    Let's go with option 2.                                      │
│                                                                        │
│  Claude: Good choice. Here's how to refactor...                       │
└────────────────────────────────────────────────────────────────────────┘
 [Esc] close preview  [↑/↓] scroll  [o] open in Claude Code
```

---

## Opening a Session

Pressing `o` (or selecting and pressing Enter with focus on a row) runs:

```bash
claude --resume {sessionId}
```

This opens the session in Claude Code, returning focus to the user. They can now:
- Reply to Claude
- Use `/clear` to dismiss when done (triggers the `endSession` hook)
- Work as normal

---

## Refresh Behavior

- On launch: scan all `.jsonl` files in `~/.claude/projects/` and subdirectories
- On `r` key: re-scan
- No auto-refresh (user manually restarts TUI when needed)

---

## Implementation Notes

**Language:** Python 3.10+

**TUI Library:** [Rich](https://rich.readthedocs.io/) (for rendering) + [Textual](https://textual.textualize.io/) (for interactive TUI framework)

**Package Manager:** [uv](https://docs.astral.sh/uv/) for running and dependency management

**Project Structure:**
```
agent-dashboard/
├── pyproject.toml          # uv project config
├── spec.md                 # this file
├── main.py                 # entry point
└── src/
    ├── parser.py           # JSONL parsing, session loading
    ├── ui.py               # Textual app and views
    └── dismiss.py          # Dismissal log management
```

**Parsing:**
- Scan `~/.claude/projects/` recursively for `.jsonl` files
- For each file, read all lines and identify the `sessionId` and `ai-title`
- Extract the last `assistant` message for preview
- Compute elapsed time from the last message's `timestamp`

**Dismissal Logic:**
- Read `~/.claude/sessions.log` on startup and after each dismiss
- Filter out any session whose `sessionId` appears in the log
- When user presses `d`, append `sessionId\n` to the file

---

## Hook Configuration

Users will need to set up the `endSession` hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "endSession": "bash ~/.claude/hooks/dismiss-session.sh"
  }
}
```

And create `~/.claude/hooks/dismiss-session.sh`:

```bash
#!/bin/bash
# Appends the current session ID to the dismissal log
# Claude Code passes sessionId via $CLAUDE_SESSION_ID environment variable
if [ -n "$CLAUDE_SESSION_ID" ]; then
  echo "$CLAUDE_SESSION_ID" >> ~/.claude/sessions.log
  echo "Session $CLAUDE_SESSION_ID dismissed (cheerio)"
else
  echo "Error: CLAUDE_SESSION_ID not set" >&2
  exit 1
fi
```

---

## Out of Scope (v1)

- Replying from within the TUI
- Searching/filtering sessions
- Starred or pinned sessions
- Custom session ordering
- Archiving vs. deletion distinction

---

## Implementation Clarifications

### 1. Hook Argument Passing

**Decision:** Session ID passed via environment variable `$CLAUDE_SESSION_ID`

**Rationale:**
- More reliable across shell contexts and languages
- Clearer in hook configuration (no ambiguity about positional args)
- Language-agnostic (works with any hook script)
- Standard Unix convention for passing context to child processes

### 2. CLI Syntax for Resuming Sessions

**Decision:** `claude --resume {sessionId}`

Confirmed. This opens the session in Claude Code with full context restored.

### 3. Dismissal State Storage

**Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A** (Recommended) | Single text file: `~/.claude/sessions.log` | Simple, transparent, auditable, human-readable | Append-only (grows over time, needs occasional cleanup) |
| **B** | Per-session marker: `.dismissed` file in each session dir | Atomic, easy to undo (delete marker), scattered state | Harder to audit globally, file system sprawl |
| **C** | Structured JSON: `~/.claude/dismissed-sessions.json` | Can include metadata (time, reason), structured | JSON parsing overhead, more complex |
| **D** | Organized text: `~/.claude/state/dismissed.txt` | Same as A but organized | Just organizational (functionally identical to A) |

**Recommendation:** **Option A** (`~/.claude/sessions.log`)

**Why:**
- Simplicity: one plain text file, one session ID per line
- Transparency: users can inspect and manually edit if needed (e.g., undo a dismissal)
- Auditability: full history of all dismissed sessions
- Low overhead: no parsing, just line-by-line reads
- Unix philosophy: simple tools, simple formats
- If growth is a concern, users can archive old entries (rotate the log)

The dismissal log is the source of truth: on every TUI start and refresh, read this file and filter those session IDs from the active list.
