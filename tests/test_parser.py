"""Tests for session parser and time formatting."""

import pytest
from datetime import datetime, timedelta
from src.parser import format_elapsed_time


class TestElapsedTimeFormatting:
    """Test suite for elapsed time formatting."""

    def test_elapsed_time_just_now(self):
        """Times less than 1 minute old should show 'just now'."""
        timestamp = datetime.now() - timedelta(seconds=30)
        result = format_elapsed_time(timestamp)
        assert result == "just now", f"Expected 'just now', got '{result}'"

    def test_elapsed_time_minutes(self):
        """Times between 1-59 minutes old should show minutes."""
        timestamp = datetime.now() - timedelta(minutes=30)
        result = format_elapsed_time(timestamp)
        assert result == "30m ago", f"Expected '30m ago', got '{result}'"

    def test_elapsed_time_one_minute(self):
        """Time exactly 1 minute old should show '1m ago'."""
        timestamp = datetime.now() - timedelta(minutes=1)
        result = format_elapsed_time(timestamp)
        assert result == "1m ago", f"Expected '1m ago', got '{result}'"

    def test_elapsed_time_hours(self):
        """Times between 1-23 hours old should show hours."""
        timestamp = datetime.now() - timedelta(hours=2)
        result = format_elapsed_time(timestamp)
        assert result == "2h ago", f"Expected '2h ago', got '{result}'"

    def test_elapsed_time_one_hour(self):
        """Time exactly 1 hour old should show '1h ago'."""
        timestamp = datetime.now() - timedelta(hours=1)
        result = format_elapsed_time(timestamp)
        assert result == "1h ago", f"Expected '1h ago', got '{result}'"

    def test_elapsed_time_days(self):
        """Times between 1-6 days old should show days."""
        timestamp = datetime.now() - timedelta(days=3)
        result = format_elapsed_time(timestamp)
        assert result == "3d ago", f"Expected '3d ago', got '{result}'"

    def test_elapsed_time_one_day(self):
        """Time exactly 1 day old should show '1d ago'."""
        timestamp = datetime.now() - timedelta(days=1)
        result = format_elapsed_time(timestamp)
        assert result == "1d ago", f"Expected '1d ago', got '{result}'"

    def test_elapsed_time_weeks(self):
        """Times 7+ days old should show weeks."""
        timestamp = datetime.now() - timedelta(weeks=2)
        result = format_elapsed_time(timestamp)
        assert result == "2w ago", f"Expected '2w ago', got '{result}'"

    def test_elapsed_time_one_week(self):
        """Time exactly 1 week old should show '1w ago'."""
        timestamp = datetime.now() - timedelta(weeks=1)
        result = format_elapsed_time(timestamp)
        assert result == "1w ago", f"Expected '1w ago', got '{result}'"

    def test_elapsed_time_boundary_59_seconds(self):
        """At 59 seconds, should still show 'just now'."""
        timestamp = datetime.now() - timedelta(seconds=59)
        result = format_elapsed_time(timestamp)
        assert result == "just now", f"Expected 'just now', got '{result}'"

    def test_elapsed_time_boundary_60_seconds(self):
        """At 60 seconds (1 minute), should show '1m ago'."""
        timestamp = datetime.now() - timedelta(seconds=60)
        result = format_elapsed_time(timestamp)
        assert result == "1m ago", f"Expected '1m ago', got '{result}'"

    def test_elapsed_time_boundary_hour(self):
        """At 59 minutes, should show minutes, not hours."""
        timestamp = datetime.now() - timedelta(minutes=59)
        result = format_elapsed_time(timestamp)
        assert result == "59m ago", f"Expected '59m ago', got '{result}'"

    def test_elapsed_time_boundary_day(self):
        """At 23 hours 59 minutes, should show hours, not days."""
        timestamp = datetime.now() - timedelta(hours=23, minutes=59)
        result = format_elapsed_time(timestamp)
        assert "h ago" in result, f"Expected hours format, got '{result}'"

    def test_elapsed_time_boundary_week(self):
        """At 6 days 23 hours, should show days, not weeks."""
        timestamp = datetime.now() - timedelta(days=6, hours=23)
        result = format_elapsed_time(timestamp)
        assert "d ago" in result, f"Expected days format, got '{result}'"
