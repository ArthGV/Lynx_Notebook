# Modern Notebook Redesign (opencode / Claude Code style)

## Goal
Make the notebook TUI read as a modern terminal tool like opencode / Claude Code:
no box borders, minimal chrome, message-style cells with label rows, subtle
accent-limited palette, clear focus depth, minimal insert controls, empty-cell
hints.

## Design decisions (confirmed with user)
- Cell identity: **label rows** (`[1] code`, `[2] md`) + colored gutter rail
- Inserts: **minimal `+`**, expands to `+ code` / `md` on hover
- Empty cells: **dim placeholder hints**

---

## File 1: `lynx_notebook/tui/app.py`

### 1.1 Kill the classic chrome
In `NotebookApp.compose()`, remove `yield Header()` and `yield Footer()`.
Add a slim status bar instead:
```python
yield Static("", id="app-status")
```
(Import `Static` already present; drop `Header`, `Footer` from the widgets import.)

Add a helper and call it from `on_mount`, `_focus_cell`, `_refresh_cells`:
```python
def _update_status(self) -> None:
    bar = self.query_one("#app-status", Static)
    path = self.path or "new notebook.lxnb"
    n = len(self.cell_widgets)
    cur = f"cell {self.focused_cell_index + 1}/{n}" if n else "no cells"
    bar.update(f"{path}    {cur}")
```

### 1.2 Message-style cell structure (CodeCell & MarkdownCell)
Rework `compose()` to a frame with a colored rail + label row:

```python
def compose(self) -> ComposeResult:
    self.rail   = Static("▍", classes="cell-rail code-rail")
    self.label  = Static("", classes="cell-label code-label")
    self.bar    = Static("", classes="cell-bar")
    self.bar.visible = False
    ... build editor/output/error as today ...

    with Horizontal(classes="cell-frame"):
        yield self.rail
        with Vertical(classes="cell-main"):
            yield self.label
            yield self.bar
            with Vertical(classes="cell-body"):
                yield editor, output, error
```
MarkdownCell mirrors this with `md-rail` / `md-label` classes, plus its renderer.

Add `_update_label()` on both cells (also refresh `self.label`):
```python
TYPE_TAG = {CellType.CODE: "code", CellType.MARKDOWN: "md"}

def _update_label(self) -> None:
    idx = self.index + 1
    hint = ""
    if not self.cell.source.strip() and not self._collapsed:
        hint = "  # start typing" if self.cell.type == CellType.CODE else "  # markdown"
    self.label.update(f"[{idx}] {TYPE_TAG[self.cell.type]}{hint}")
```
Call `_update_label()` in `__init__`/compose and after `exit_edit`/`set_collapsed`.
(`CellType.value` is "code"/"markdown" — the `TYPE_TAG` map collapses it to
"code"/"md" for short labels.)

Note: `self.index` is passed at construction and cells are rebuilt on insert/delete,
so label indices stay correct.

### 1.3 Minimal insert control
Rework `InsertBar` to a `Horizontal` (classes `insert-bar`) with:
- spacer `width: 1fr` (keep buttons right-aligned), plus
- `Button("+", id=f"insert-{i}-code", classes="insert-btn insert-code")`
- `Button("md", id=f"insert-{i}-md", classes="insert-btn insert-md")`

Both invisible by default (CSS), revealed on `.insert-bar:hover`.

Update `on_insert_press` to parse id refs `insert-{i}-code` / `insert-{i}-md`.

### 1.4 Output / error prefixes
In `CodeCell.update_from_result`, prefix lines so terminal output reads modern:
```python
output  -> "\n".join("› " + line for line in result.output)
error   -> "✗ " + result.error   # first line only; keep rest raw
```

---

## File 2: `lynx_notebook/tui/theme.py`

### 2.1 Prune to an 8-color palette
Replace the constants block (lines 7-28) with:
```python
BG_COLOR        = "#0c0e12"   # screen
CELL_BG         = "#14171c"   # inactive cell
CELL_FOCUS_BG   = "#1b2028"   # active / focused cell
TEXT            = "#e2e6ee"
MUTED           = "#5d6a78"
DIM             = "#2a3440"   # hints, separators, inactive controls
CODE_ACCENT     = "#5da2ff"
CODE_ACCENT_DIM = "#27486f"   # inactive code rail
MD_ACCENT       = "#b493e0"
MD_ACCENT_DIM   = "#544a73"   # inactive md rail
ERROR           = "#e56b6b"
OUTPUT          = "#8b98a5"
```
Delete: `SECONDARY_BG`, `CODE_BORDER`, `FOCUS_ACCENT`, `MD_BORDER`,
`MD_TEXT`, `ACCENT`, `INSERT_ZONE`, `HEADER_BG`, `HEADER_TEXT`,
`COLLAPSED_HEADER`, `MD_EDIT_*`, `CODE_LEFT_LINE`, `MD_LEFT_LINE`.

### 2.2 Editor theme (update `editor_theme()`)
```python
base_style=Style(color=TEXT, bgcolor=CELL_BG),
gutter_style=Style(color=MUTED, bgcolor=CELL_BG),
cursor_style=Style(color=BG_COLOR, bgcolor=CODE_ACCENT, bold=True),   # block cursor
cursor_line_gutter_style=Style(color=MUTED, bgcolor=CELL_BG),
cursor_line_style=Style(bgcolor=CELL_FOCUS_BG),
selection_style=Style(bgcolor="#2b3850"),
bracket_matching_style=Style(color=CODE_ACCENT, bold=True),
```

### 2.3 Rewrite CSS in `build_css()`
- `Screen { background: $bg; color: $text; }`
- `#cell-list { background: $bg; padding: 0 3 0 0; overflow-y: auto; }`
- `#app-status { dock: bottom; height: 1; padding: 0 2; background: $bg; color: $muted; }`
- **Cell frame**:
  ```css
  .cell-frame { height: auto; }
  .cell-rail  { width: 1; color: $muted; background: transparent; }
  .cell-main  { padding: 0 0 0 1; height: auto; }
  .code-rail  { color: $code-accent-dim; }
  .md-rail    { color: $md-accent-dim; }
  .cell-label { height: 1; color: $muted; }
  .code-label { color: $code-accent; }
  .md-label   { color: $md-accent; }
  ```
- **Focus depth** (bright rail + lifted bg on the active cell):
  ```css
  .cell:focus-within { background: $cell-focus-bg; }
  .cell:focus-within .code-rail { color: $code-accent; }
  .cell:focus-within .md-rail   { color: $md-accent; }
  ```
- Editors/render: keep `border: none`, no outer box inside the frame.
- `.code-editor, .md-editor { height: auto; min-height: 2; }`
- `.md-render { height: auto; min-height: 2; }`
- **Outputs**:
  ```css
  .cell-output { color: $output; padding: 0 0 0 1; height: auto; }
  .cell-error  { color: $error;  padding: 0 0 0 1; height: auto; }
  ```
- **Collapsed bar**: `height: 1; color: $muted; background: $cell-bg;`
- **Insert bar** (hidden controls, revealed on hover):
  ```css
  .insert-bar { height: 1; }
  .insert-btn { display: none; background: transparent; color: $muted;
                border: none; height: 1; padding: 0 1; }
  .insert-bar:hover .insert-btn { display: block; }
  .insert-btn:hover { color: $text; background: $cell-focus-bg; }
  .insert-code:hover { color: $code-accent; }
  .insert-md:hover   { color: $md-accent; }
  ```

### 2.4 CSS variables
Update the `$var:` header block to the new constants only.

---

## Verification
- `python -c "from lynx_notebook.tui.theme import build_css; build_css()"`
- `python -c "from lynx_notebook.tui.app import NotebookApp"`
- Run `python -m lynx_notebook <file>` and check visually: focus depth, label
  rows, hint text, insert-on-hover, no box borders, status bar.
- Run existing tests (`pytest` if present).

## Notes / risks
- `:focus-within` is **supported** in Textual 8.2.8 (verified) — no fallback needed.
- Removing `Header`/`Footer` removes binding hints; status bar on the right can
  show `ctrl+enter run · ctrl+n code · ctrl+m md` instead.
- `CellType.value` is "code"/"markdown" — use a `TYPE_TAG` map → "code"/"md".
- Buttons hidden with `display: none` won't receive hover until parent hover —
  intended behaviour (reveal on hover over the 1-row insert zone).