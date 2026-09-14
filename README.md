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

```
───────────────────────────────────────────────
  │ >> 'result is'
  │ >> x * 2                      ← code cell (single border)
  ───────────────────────────────────────────────
        result is
        20                                        ← output (indented, plain text)
  ····· + ·····                                    ← hover zone to insert a cell
  ═══════════════════════════════════════════════
            # My Analysis
            Rendered markdown here.               ← markdown cell (double border)
  ═══════════════════════════════════════════════
```

- Code cells get a solid single border; markdown cells render inline with a
  double border. `Enter` toggles a markdown cell into raw-edit mode (border flips
  to single).
- Notebooks auto-save on cell run, insert, delete, and close.
- Catching an error keeps it inline in the output area (red text) and state from
  earlier cells is preserved.

#### Keybindings

| Key | Action |
|---|---|
| `Ctrl+Enter` | Run current cell |
| `Ctrl+Shift+Enter` | Run all cells |
| `Ctrl+N` / `Ctrl+M` | Insert code / markdown cell after current |
| `Ctrl+Up` / `Ctrl+Down` | Jump between cells |
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
    └── theme.py        # ALL colors in one file; build_css() compiles them
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