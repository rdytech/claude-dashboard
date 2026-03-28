"""
Session discovery and JSONL parsing.

Scans ~/.claude/projects/ for session files and extracts metadata.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Session:
    """Represents a Claude Code session."""

    session_id: str
    project_name: str
    title: str
    last_message_timestamp: datetime
    last_assistant_message: str
    full_message_history: list[dict]


def discover_sessions() -> list[Session]:
    """
    Discover all sessions in ~/.claude/projects/ recursively.

    Returns:
        List of Session objects, or empty list if directory doesn't exist.
    """
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        return []

    sessions = []

    # Find all .jsonl files recursively
    for jsonl_file in projects_dir.glob("**/*.jsonl"):
        try:
            session = parse_jsonl(jsonl_file)
            if session:
                sessions.append(session)
        except Exception as e:
            # Log but continue on parse errors
            print(f"Warning: Failed to parse {jsonl_file}: {e}")

    # Sort by most recent activity first
    sessions.sort(key=lambda s: s.last_message_timestamp, reverse=True)

    return sessions


def parse_jsonl(filepath: Path) -> Optional[Session]:
    """
    Parse a single JSONL session file.

    Args:
        filepath: Path to the .jsonl file

    Returns:
        Session object or None if parsing fails
    """
    lines = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
    except Exception:
        return None

    if not lines:
        return None

    # Extract session ID (from any message, they all have the same session_id)
    session_id = None
    for msg in lines:
        if "sessionId" in msg:
            session_id = msg["sessionId"]
            break

    if not session_id:
        return None

    # Extract project name from filepath
    # Path format: ~/.claude/projects/{project}/{sessionId}.jsonl
    # or: ~/.claude/projects/-/{sessionId}.jsonl
    relative_parts = filepath.relative_to(Path.home() / ".claude" / "projects").parts
    if len(relative_parts) >= 2:
        project_name = relative_parts[0]
    else:
        project_name = "-"

    # Find ai-title or fallback to first user message
    title = _extract_title(lines)

    # Get last message timestamp
    last_timestamp = None
    for msg in reversed(lines):
        if "timestamp" in msg:
            try:
                last_timestamp = datetime.fromisoformat(msg["timestamp"])
                break
            except (ValueError, TypeError):
                pass

    if not last_timestamp:
        last_timestamp = datetime.now()

    # Extract last assistant message for preview
    last_assistant_msg = _extract_last_assistant_message(lines)

    return Session(
        session_id=session_id,
        project_name=project_name,
        title=title,
        last_message_timestamp=last_timestamp,
        last_assistant_message=last_assistant_msg,
        full_message_history=lines,
    )


def _extract_title(lines: list[dict]) -> str:
    """
    Extract session title from ai-title field or first user message.

    Args:
        lines: List of message dictionaries from JSONL

    Returns:
        Title string, truncated to ~40 chars. Defaults to "[Untitled]"
    """
    # First, look for ai-title
    for msg in lines:
        if msg.get("type") == "ai-title":
            title = msg.get("message", {}).get("content", "").strip()
            if title:
                return _truncate(title, 40)

    # Fallback to first user message
    for msg in lines:
        if msg.get("message", {}).get("role") == "user":
            content = msg.get("message", {}).get("content", "")
            text = _extract_text_from_content(content)
            if text:
                # Get first line only
                first_line = text.split("\n")[0]
                return _truncate(first_line, 40)

    return "[Untitled]"


def _extract_last_assistant_message(lines: list[dict]) -> str:
    """
    Extract the last assistant message for preview.

    Args:
        lines: List of message dictionaries from JSONL

    Returns:
        First line of last assistant message, or empty string
    """
    for msg in reversed(lines):
        if msg.get("message", {}).get("role") == "assistant":
            content = msg.get("message", {}).get("content", "")
            text = _extract_text_from_content(content)
            if text:
                # Get first line only
                first_line = text.split("\n")[0]
                return _truncate(first_line, 70)

    return ""


def _extract_text_from_content(content) -> str:
    """
    Extract plain text from message content.

    Content can be either a string or a list of structured objects.

    Args:
        content: Either a string or a list of dicts with type/text fields

    Returns:
        Plain text string
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        # Collect text from structured content blocks
        texts = []
        for block in content:
            if isinstance(block, dict):
                # Extract text blocks (ignore thinking, images, etc.)
                if block.get("type") == "text" and "text" in block:
                    texts.append(block["text"])
        return " ".join(texts).strip()

    return ""


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def format_elapsed_time(timestamp: datetime) -> str:
    """
    Format elapsed time from timestamp to now.

    Args:
        timestamp: datetime object

    Returns:
        Human-readable elapsed time string (e.g., "2h ago", "just now")
    """
    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
    elapsed = now - timestamp

    seconds = int(elapsed.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"
    else:
        weeks = seconds // 604800
        return f"{weeks}w ago"
