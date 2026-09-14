from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import CellType


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lynx-notebook",
        description="TUI notebook for the Lynx programming language.",
    )
    parser.add_argument("file", nargs="?", help=".lxnb notebook file to open")
    parser.add_argument("--run", action="store_true", help="run all cells and exit (headless)")
    args = parser.parse_args()

    engine = NotebookEngine()

    if args.file is None:
        notebook = engine.new_notebook()
        notebook.add_cell(CellType.CODE)
        _launch_tui(engine, notebook, path=None)
        return

    path = Path(args.file)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        sys.exit(1)

    notebook = engine.load(path)

    if args.run:
        _headless_run(engine, notebook)
    else:
        _launch_tui(engine, notebook, path=path)


def _headless_run(engine: NotebookEngine, notebook) -> None:
    from lynx_notebook.models import Cell

    for cell in notebook.cells:
        if cell.type != CellType.CODE:
            continue
        result = engine.execute_cell(cell, notebook)
        for line in result.output:
            print(line)
        if result.error:
            print(result.error, file=sys.stderr)
            sys.exit(1)


def _launch_tui(engine: NotebookEngine, notebook, path: Path | None) -> None:
    from lynx_notebook.tui.app import NotebookApp

    app = NotebookApp(engine=engine, notebook=notebook, path=path)
    app.run()


if __name__ == "__main__":
    main()
