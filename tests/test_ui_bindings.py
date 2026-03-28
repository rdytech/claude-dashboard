"""Tests for UI key binding configuration."""

from src.ui import PendingSessionsApp


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

