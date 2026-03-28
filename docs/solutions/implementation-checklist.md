# Implementation Checklist: Textual TUI + Claude Code Integration

Use this checklist when building similar applications that integrate with Claude Code sessions.

## Phase 1: Data Inspection & Parser Development

- [ ] **Inspect real session files**
  - [ ] Read actual `.jsonl` from `~/.claude/projects/`
  - [ ] Sample 5-10 files to understand variation
  - [ ] Note all message content types (string, list, nested objects)

- [ ] **Implement parser independently**
  - [ ] Create data classes for session metadata
  - [ ] Test on real files with error handling
  - [ ] Handle both string and structured content formats
  - [ ] Implement robust title/preview extraction with fallbacks

- [ ] **Test parser without UI**
  ```bash
  python -c "from src.parser import discover_sessions; print(discover_sessions())"
  ```

## Phase 2: Build Textual App Structure

- [ ] **Set up pyproject.toml correctly**
  - [ ] Specify `[tool.hatch.build.targets.wheel] packages = ["src"]` if using src layout
  - [ ] Include Textual and Rich in dependencies

- [ ] **Create custom widgets**
  - [ ] ✅ Always use `def __init__(self, ..., **kwargs)` in custom widgets
  - [ ] ✅ Call `super().__init__(**kwargs)` to pass through `id`, `classes`, etc.
  - [ ] Don't populate children in `__init__()` — defer to `on_mount()` or later

- [ ] **Implement compose() method**
  - [ ] Define all widgets (Header, Footer, custom views)
  - [ ] Use container layouts (Vertical, Horizontal) for structure
  - [ ] Assign IDs for query access: `self.query_one("#my-id", MyWidget)`

- [ ] **Add key bindings**
  - [ ] Define `BINDINGS` class attribute
  - [ ] Create action methods: `def action_my_action(self)`
  - [ ] Test with simple navigation (up/down arrows) first

## Phase 3: Subprocess Integration (The Tricky Part)

- [ ] **Never call subprocess directly in action handlers**
  - [ ] ❌ Don't do: `subprocess.run([...])` inside `action_open_session()`
  - [ ] ✅ Do: `self.exit(result=session_data)` and handle in caller

- [ ] **Use app return value as sync point**
  ```python
  # main.py
  def main():
      app = MyApp()
      result = app.run()  # Blocks until app fully closes

      if result:
          # Now terminal is fully restored
          subprocess.run([...])
  ```

- [ ] **Test subprocess launch**
  - [ ] Open app
  - [ ] Trigger subprocess launch
  - [ ] Verify terminal is clean (no TUI artifacts)
  - [ ] Verify subprocess is responsive (not frozen)

## Phase 4: Content Rendering

- [ ] **Handle structured content in all render methods**
  ```python
  from src.parser import _extract_text_from_content

  def render(self):
      content = msg.get("message", {}).get("content", "")
      text = _extract_text_from_content(content)  # Handles both string and list
      return text
  ```

- [ ] **Test with real rich content**
  - [ ] Preview pane should show text messages correctly
  - [ ] Ignore thinking blocks and images gracefully
  - [ ] Truncate long messages appropriately

## Phase 5: Testing & Deployment

- [ ] **Unit test each module independently**
  ```bash
  python -m py_compile src/*.py main.py
  python -c "from src.parser import discover_sessions; ..."
  python -c "from src.ui import MyApp; app = MyApp(); print('OK')"
  ```

- [ ] **Manual testing flow**
  - [ ] Run app and verify session list appears
  - [ ] Test all key bindings
  - [ ] Test dismiss/refresh logic
  - [ ] Test opening session (no overlay)
  - [ ] Test preview pane with various message types

- [ ] **Document module dependencies**
  - [ ] List what each module needs from others
  - [ ] Make imports explicit and testable

## Debugging Checklist

**Issue: "AttributeError: 'list' object has no attribute 'split'"**
- Cause: Trying to `.split()` on message content that's a list
- Fix: Use `_extract_text_from_content()` helper

**Issue: "TypeError: widget.__init__() got unexpected keyword argument 'id'"**
- Cause: Custom widget doesn't accept `**kwargs`
- Fix: Add `**kwargs` to `__init__()` and pass to `super().__init__(**kwargs)`

**Issue: "MountError: Can't mount widget before attached"**
- Cause: Calling `append()` in `__init__()` before widget is mounted
- Fix: Defer child population to `on_mount()` or call `update()` after mount

**Issue: "Subprocess frozen / unresponsive"**
- Cause: Launching subprocess while Textual terminal state (raw mode, alt screen) is active
- Fix: Use `self.exit(result=...)` and handle subprocess in main.py after app.run() returns

**Issue: "Session appears overlaid / unreadable"**
- Cause: Same as above — terminal not fully restored
- Fix: Ensure subprocess call happens after `app.run()` fully completes

## File Locations Reference

| What | Where |
|------|-------|
| Claude Code sessions | `~/.claude/projects/{project}/{sessionId}.jsonl` |
| Default context | `~/.claude/projects/-/{sessionId}.jsonl` |
| Dismissal log | `~/.claude/sessions.log` |
| Settings | `~/.claude/settings.json` |

## Textual Best Practices

1. **Use `self.query_one(selector, WidgetType)` for direct access**
   ```python
   widget = self.query_one("#my-id", MyWidget)
   ```

2. **Render methods should be pure** (no side effects)
   - Called frequently for updates
   - Should return string representation only

3. **Use binding.py conventions**
   - `action_` prefix for methods
   - Match key to method: `"o"` → `action_open_session()`

4. **CSS styling is powerful**
   - Define `DEFAULT_CSS` on widgets
   - Use selectors: `#id`, `.class`, `WidgetName`

5. **Async context**
   - App lifecycle is async
   - Action handlers are sync (run in async context via `run_sync()`)
   - Never await inside action handlers

## Reference Code Snippets

**Parsing JSONL with error handling:**
```python
def parse_jsonl(filepath):
    lines = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    lines.append(json.loads(line))
    except Exception as e:
        print(f"Warning: {filepath} failed to parse: {e}")
        return None

    return lines if lines else None
```

**Extracting session metadata:**
```python
session_id = None
for msg in lines:
    if "sessionId" in msg:
        session_id = msg["sessionId"]
        break

timestamp = None
for msg in reversed(lines):
    if "timestamp" in msg:
        try:
            timestamp = datetime.fromisoformat(msg["timestamp"])
            break
        except (ValueError, TypeError):
            pass
```

**Safe subprocess launch:**
```python
# In main.py
def main():
    app = PendingSessionsApp()
    session_id = app.run()  # Blocks until fully exited

    if session_id:
        subprocess.run(["claude", "--resume", session_id])
```

---

**Version:** 1.0
**Last Updated:** 2026-03-28
**Relevant Projects:** agent-dashboard
