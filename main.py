#!/usr/bin/env python3
"""
Agent Dashboard - TUI for managing pending Claude Code sessions.
"""

import subprocess
from src.ui import PendingSessionsApp


def main():
    """Entry point for the TUI application."""
    app = PendingSessionsApp()
    session_id = app.run()

    # If a session ID was returned, the user opened a session
    # Launch Claude Code now that the TUI has fully exited
    if session_id:
        subprocess.run(["claude", "--resume", session_id])


if __name__ == "__main__":
    main()
