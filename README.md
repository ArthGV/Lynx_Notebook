# Lynx Notebook

A terminal notebook for the [Lynx](https://github.com/your-user/Lynx) programming
language. Run code in cells, see per-cell output, and share state between cells —
all saved to a `.lxnb` file.

## Install

```bash
# from this repo (requires lynx installed, e.g. pip install -e /path/to/Lynx)
pip install -e ".[dev]"
```

## Usage

```bash
lynx-notebook                    # open the TUI with a new notebook
lynx-notebook notes.lxnb         # open an existing notebook in the TUI
lynx-notebook notes.lxnb --run   # headless: run all cells, print outputs, stop on error
```

## TUI

- Cells are soft cards on a quiet background; the focused cell gets an accent
  border, hover reveals the `×` delete button and the `+` insert bar.
- Markdown cells render inline. Click one (or focus it) to edit; blur or
  `Ctrl+Enter` renders it again.
- `Ctrl+[` folds the focused cell to a one-line `▸` preview; `Ctrl+]` (or a
  click on the preview) expands it.
- Notebooks auto-save on cell run, insert, delete, and close.
- Errors stay inline in the output area (red rail) and state from earlier cells
  is preserved.

#### Theming

Every color, spacing value and glyph lives in
`lynx_notebook/tui/themes/default.json` (light and dark palettes, syntax colors,
paddings, glyphs). To customise, copy only the keys you want to change into
`~/.config/lynx-notebook/theme.json`; it is merged over the defaults (a broken
file is ignored with a message). `LYNX_THEME=light|dark` overrides `mode` for one
run, and `mode: "auto"` follows the terminal background. `Ctrl+T` toggles
light/dark live. Fonts are chosen in your terminal emulator, not the app.

#### Keybindings

| Key | Action |
|---|---|
| `Ctrl+Enter` | Run current cell |
| `Ctrl+Shift+Enter` | Run all cells |
| `Ctrl+N` / `F2` | Insert code / markdown cell after current |
| `Ctrl+Up` / `Ctrl+Down` | Jump between cells |
| `Ctrl+T` | Toggle light / dark theme |
| `Ctrl+[` / `Ctrl+]` | Collapse / expand current cell |
| `Ctrl+Backspace` | Delete current cell |
| `Ctrl+Q` | Save & quit |

## Architecture

```
lynx_notebook/
├── engine.py           # NotebookEngine — frontend-agnostic: execute cells, hold state
├── capture.py          # OutputCapture — redirects lynx stdout per cell
├── models.py           # Cell, CellResult, Notebook dataclasses
├── serialization.py    # .lxnb JSON read/write
├── cli.py              # entry point
└── tui/
    ├── app.py          # Textual app + cell widgets
    ├── theme.py        # loads the theme, builds editor theme + stylesheet
    └── themes/default.json  # ALL colors, spacing, glyphs
```

The engine has no UI dependency — `test_engine.py` runs cells headlessly. The
reusable core can back other frontends (macOS, web, VS Code) later.

Cell execution captures whatever `>>` prints via `contextlib.redirect_stdout`,
so the language itself is untouched.

## File format (`.lxnb`)

```json
{
  "version": 1,
  "cells": [
    { "id": "a1b2c3d4", "type": "code", "source": ">> 1 + 1",
      "output": ["2"], "error": null, "execution_count": 1 },
    { "id": "e5f6g7h8", "type": "markdown", "source": "# Notes",
      "output": [], "error": null, "execution_count": null }
  ],
  "metadata": { "kernel": "lynx" }
}
```

## Tests

```bash
python -m pytest tests/
```

## Roadmap

- [ ] Drag-to-reorder cells
- [ ] Tree-sitter grammar for Lynx (syntax highlighting in the editor)
- [ ] SQL-style table rendering for `table` outputs