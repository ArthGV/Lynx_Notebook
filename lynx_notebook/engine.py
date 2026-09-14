from __future__ import annotations

from pathlib import Path

from src.runtime.environment import Environment

from lynx_notebook.capture import execute_cell_source
from lynx_notebook.models import Cell, CellResult, CellType, Notebook
from lynx_notebook import serialization


class NotebookEngine:
    def __init__(self) -> None:
        self.env = Environment()

    def execute_cell(self, cell: Cell, notebook: Notebook) -> CellResult:
        if cell.type != CellType.CODE:
            return CellResult(output=[], error=None, execution_count=0)

        exec_count = notebook.next_exec_count()
        result = execute_cell_source(cell.source, self.env)
        result.execution_count = exec_count

        cell.output = result.output
        cell.error = result.error
        cell.execution_count = exec_count
        return result

    def execute_all(self, notebook: Notebook) -> list[CellResult]:
        results = []
        for cell in notebook.cells:
            if cell.type == CellType.CODE:
                results.append(self.execute_cell(cell, notebook))
            else:
                results.append(CellResult(output=[], error=None, execution_count=0))
        return results

    def load(self, path: str | Path) -> Notebook:
        return serialization.load(path)

    def save(self, notebook: Notebook, path: str | Path) -> None:
        serialization.save(notebook, path)

    def new_notebook(self) -> Notebook:
        return Notebook()
