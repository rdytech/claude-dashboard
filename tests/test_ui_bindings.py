"""Tests for UI key binding configuration and configurable filter."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.ui import PendingSessionsApp, is_within_cutoff, DEFAULT_DAYS_FILTER
from src.parser import discover_sessions


class TestEnterKeyBinding:

    def _get_binding(self, key: str):
        for binding in PendingSessionsApp.BINDINGS:
            if binding.key == key:
                return binding
        return None

    def test_enter_binding_has_priority(self):
        """Enter binding must have priority=True to override ListView's built-in enter handler.

        ListView intercepts 'enter' at the widget level before it can bubble up
        to the app. Without priority=True, the app-level binding is silently ignored.
        """
        binding = self._get_binding("enter")
        assert binding is not None and binding.priority is True, (
            "The 'enter' binding must have priority=True. "
            "ListView's built-in handler intercepts 'enter' before app-level bindings "
            "fire — priority=True is required to override it."
        )


def _write_session_at(session_id: str, project_dir: Path, timestamp: datetime) -> Path:
    """Create a JSONL session file with a specific timestamp."""
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    jsonl_file = project_dir / f"{session_id}.jsonl"
    with open(jsonl_file, "w") as f:
        f.write(json.dumps({"sessionId": session_id, "timestamp": ts_str,
                            "message": {"role": "user", "content": "hello"}}) + "\n")
        f.write(json.dumps({"sessionId": session_id, "timestamp": ts_str,
                            "message": {"role": "assistant", "content": "hi"}}) + "\n")
    return jsonl_file


class TestFilterBinding:
    """The 'f' key binding must exist and trigger the filter action."""

    def _get_binding(self, key: str):
        for binding in PendingSessionsApp.BINDINGS:
            if binding.key == key:
                return binding
        return None

    def test_f_binding_exists(self):
        """The 'f' key must be bound to action_open_filter."""
        binding = self._get_binding("f")
        assert binding is not None, "No 'f' binding found in PendingSessionsApp.BINDINGS."
        assert binding.action == "open_filter", (
            f"Expected 'f' to trigger 'open_filter', got '{binding.action}'."
        )


class TestConfigurableDaysFilter:
    """The date filter cutoff should be adjustable at runtime via _days_filter.

    When _days_filter is 0, no date filtering should occur (show all sessions).
    When _days_filter is a positive integer, only sessions within that many days are shown.
    """

    def test_custom_days_filter_3_days(self, tmp_path, monkeypatch):
        """With a 3-day filter, a 2-day-old session is included, a 5-day-old session is excluded."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        proj_dir = tmp_path / ".claude" / "projects" / "my-project"
        proj_dir.mkdir(parents=True)

        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        _write_session_at("recent", proj_dir, two_days_ago)
        _write_session_at("older", proj_dir, five_days_ago)

        sessions = discover_sessions()
        days_filter = 3
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_filter)
        included = [s for s in sessions if is_within_cutoff(s, cutoff)]
        ids = [s.session_id for s in included]
        assert "recent" in ids, "2-day-old session should pass a 3-day filter."
        assert "older" not in ids, "5-day-old session should be excluded by a 3-day filter."

    def test_zero_days_filter_shows_all(self, tmp_path, monkeypatch):
        """When _days_filter is 0, all sessions should be shown (no date filtering).

        The app must skip the cutoff filter entirely when days_filter == 0.
        We simulate this by importing the app's filter_sessions helper.
        """
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        proj_dir = tmp_path / ".claude" / "projects" / "my-project"
        proj_dir.mkdir(parents=True)

        ancient = datetime.now(timezone.utc) - timedelta(days=365)
        _write_session_at("ancient", proj_dir, ancient)

        from src.ui import filter_sessions
        sessions = discover_sessions()
        included = filter_sessions(sessions, days_filter=0)
        assert any(s.session_id == "ancient" for s in included), (
            "A 365-day-old session should be included when days_filter is 0 (show all)."
        )

    def test_filter_persists_default_is_7(self):
        """The default days filter value must be 7."""
        assert DEFAULT_DAYS_FILTER == 7, (
            f"Expected DEFAULT_DAYS_FILTER to be 7, got {DEFAULT_DAYS_FILTER}."
        )

    def test_parse_filter_input_valid_integer(self):
        """Valid positive integer input should be accepted."""
        from src.ui import parse_filter_input
        assert parse_filter_input("3") == 3
        assert parse_filter_input("0") == 0
        assert parse_filter_input("30") == 30

    def test_parse_filter_input_invalid_returns_none(self):
        """Non-numeric, negative, or empty input should return None (keep current filter)."""
        from src.ui import parse_filter_input
        assert parse_filter_input("") is None
        assert parse_filter_input("abc") is None
        assert parse_filter_input("-5") is None
        assert parse_filter_input("3.5") is None

    def test_subtitle_text_for_active_filter(self):
        """Subtitle should show 'Last Xd' for positive filter, 'All sessions' for 0."""
        from src.ui import filter_subtitle
        assert filter_subtitle(7) == "Last 7d"
        assert filter_subtitle(3) == "Last 3d"
        assert filter_subtitle(0) == "All sessions"

