# Claude Code Pending Sessions TUI

A keyboard-driven terminal UI to track and manage Claude Code sessions awaiting your response.

## Installation

```bash
pip install textual
```

Or use `uv`:

```bash
uv run main.py
```

## Usage

```bash
python main.py
```

This launches an interactive TUI that displays:
- All active Claude Code sessions sorted by most recent activity
- Project name, session title, time elapsed, and last message preview
- A scrollable list with keyboard navigation

## Key Bindings

| Key | Action |
|-----|--------|
| `j` / `k` or `↑` / `↓` | Navigate list |
| `Enter` / `Space` | Toggle preview pane (shows last ~5 message exchanges) |
| `o` | Open session in Claude Code |
| `d` | Dismiss session (hide from list) |
| `r` | Refresh / re-scan conversation files |
| `q` / `Ctrl+C` | Quit |

## How It Works

### Session Discovery
- Scans `~/.claude/projects/` for `.jsonl` session files
- Parses Claude Code session metadata (ID, title, messages, timestamps)
- Displays active sessions in reverse chronological order

### Dismissal
- Sessions can be marked as dismissed by pressing `d`
- Dismissed session IDs are stored in `~/.claude/sessions.log`
- Dismissed sessions are hidden from the TUI
- Can also be dismissed from within Claude Code via `/clear` command with proper hook setup

### Session Structure
```
~/.claude/projects/
├── {project-name}/
│   └── {sessionId}.jsonl    # Session messages (line-delimited JSON)
├── -/
│   └── {sessionId}.jsonl    # Default context sessions
└── (etc.)
```

## Hook Configuration (Optional)

To automatically dismiss sessions when using `/clear` in Claude Code, configure the `endSession` hook in `~/.claude/settings.json`:

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
if [ -n "$CLAUDE_SESSION_ID" ]; then
  echo "$CLAUDE_SESSION_ID" >> ~/.claude/sessions.log
  echo "Session $CLAUDE_SESSION_ID dismissed"
else
  echo "Error: CLAUDE_SESSION_ID not set" >&2
  exit 1
fi
```

## Project Structure

```
agent-dashboard/
├── pyproject.toml          # Project configuration
├── spec.md                 # Specification
├── README.md               # This file
├── main.py                 # Entry point
└── src/
    ├── __init__.py
    ├── parser.py           # Session discovery and JSONL parsing
    ├── dismiss.py          # Dismissal log management
    └── ui.py               # Textual TUI application
```

## Supported Claude Code Message Formats

The parser handles multiple message content formats:
- **String content**: Plain text messages
- **Structured content**: Lists of objects with type/text fields (used for text, thinking, images, etc.)

## Future Enhancements (Out of Scope v1)

- Replying from within the TUI
- Searching/filtering sessions
- Starred or pinned sessions
- Custom session ordering
- Archiving vs. deletion distinction
