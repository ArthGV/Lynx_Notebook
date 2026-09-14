from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field


class CellType(enum.Enum):
    CODE = "code"
    MARKDOWN = "markdown"


@dataclass
class Cell:
    type: CellType = CellType.CODE
    source: str = ""
    output: list[str] = field(default_factory=list)
    error: str | None = None
    execution_count: int | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def clear_output(self) -> None:
        self.output = []
        self.error = None
        self.execution_count = None


@dataclass
class CellResult:
    output: list[str]
    error: str | None
    execution_count: int


@dataclass
class Notebook:
    cells: list[Cell] = field(default_factory=list)
    version: int = 1
    metadata: dict = field(default_factory=lambda: {"kernel": "lynx"})
    _exec_counter: int = field(default=0, repr=False)

    def next_exec_count(self) -> int:
        self._exec_counter += 1
        return self._exec_counter

    def add_cell(self, type: CellType = CellType.CODE, source: str = "", index: int | None = None) -> Cell:
        cell = Cell(type=type, source=source)
        if index is None:
            self.cells.append(cell)
        else:
            self.cells.insert(index, cell)
        return cell

    def remove_cell(self, cell_id: str) -> None:
        self.cells = [c for c in self.cells if c.id != cell_id]
