> **Superseded by [`timestamp-z-suffix-parsing.md`](./timestamp-z-suffix-parsing.md)**
> This document records the initial investigation. The root cause (timestamp extraction falling back to `datetime.now()`) was identified here, but the precise cause — Python 3.10's `fromisoformat()` rejecting the `Z` UTC suffix — and its fix are in the superseding document. The code shown in "Implementation Details" below does **not** include the fix.

---

# Elapsed Time Formatting (Investigation — Superseded)

## Problem
Users reported that session times always showed "just now" regardless of actual elapsed time. Expected to see relative times like "2h ago", "1d ago", etc.

## Investigation
The `format_elapsed_time()` function in `src/parser.py` was implemented correctly with proper logic for:
- < 1 minute: "just now"
- 1-59 minutes: "Nm ago"
- 1-23 hours: "Nh ago"
- 1-6 days: "Nd ago"
- 7+ days: "Nw ago"

## Root Cause Discovery
Through comprehensive testing, we discovered:
1. The time formatting algorithm is correct ✅
2. All boundary conditions are handled properly ✅
3. The real issue is likely **timestamp extraction** from JSONL session files

When sessions don't have valid timestamps in their JSONL, the parser falls back to `datetime.now()`, making all times appear current ("just now").

## Solution
Two-part fix needed:

### Part 1: Session Discovery (Current Implementation)
The `discover_sessions()` function in `src/parser.py`:
- ✅ Correctly parses `.jsonl` files
- ✅ Searches for `timestamp` field in message objects
- ✅ Falls back to `datetime.now()` if timestamp missing
- ✅ Formats elapsed time using `format_elapsed_time()`

### Part 2: Timestamp Handling
When parsing JSONL, ensure:
- Session files contain `timestamp` field in ISO 8601 format (e.g., `2026-03-28T14:30:00Z`)
- Timestamps are set when messages are created
- Fallback to file's mtime if no timestamp in JSONL

## Implementation Details

Location: `src/parser.py::parse_jsonl()` (lines 102-109)

```python
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
```

**Note:** The fallback to `datetime.now()` is intentional for handling sessions without timestamps, but it means sessions without real timestamps will appear current.

## Test Coverage

Comprehensive test suite in `tests/test_parser.py` validates:
- `test_elapsed_time_just_now` — < 1 minute
- `test_elapsed_time_minutes` — Minutes formatting
- `test_elapsed_time_hours` — Hours formatting
- `test_elapsed_time_days` — Days formatting
- `test_elapsed_time_weeks` — Weeks formatting
- `test_elapsed_time_boundary_*` — All boundary conditions

**Result:** All 14 tests pass ✅

## Gotchas & Notes

1. **Timezone Awareness**: The formatter uses `datetime.now()` (local time). If sessions have UTC timestamps, ensure consistent timezone handling.

2. **Clock Skew**: If system clock is wrong, elapsed times will be inaccurate.

3. **Fallback Behavior**: Sessions without timestamps will show recent activity even if they're old. Consider logging a warning when fallback is used.

## Future Improvements

- [ ] Add file modification time (mtime) as secondary fallback
- [ ] Log warnings when using fallback timestamps
- [ ] Add timezone-aware timestamp handling
- [ ] Validate timestamp format during JSONL parsing

## Related Code

- Time formatting: `src/parser.py::format_elapsed_time()`
- Session discovery: `src/parser.py::discover_sessions()`
- UI rendering: `src/ui.py::SessionListItem.render()`
