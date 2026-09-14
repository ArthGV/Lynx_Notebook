from __future__ import annotations

import json
from pathlib import Path

from lynx_notebook.models import Cell, CellType, Notebook

CURRENT_VERSION = 1


def load(path: str | Path) -> Notebook:
    path = Path(path)
    data = json.loads(path.read_text())

    notebook = Notebook(
        version=data.get("version", CURRENT_VERSION),
        metadata=data.get("metadata", {"kernel": "lynx"}),
    )

    for raw in data.get("cells", []):
        cell_type = CellType.CODE if raw.get("type", "code") == "code" else CellType.MARKDOWN
        notebook.cells.append(Cell(
            id=raw.get("id", ""),
            type=cell_type,
            source=raw.get("source", ""),
            output=raw.get("output", []),
            error=raw.get("error"),
            execution_count=raw.get("execution_count"),
        ))

    return notebook


def save(notebook: Notebook, path: str | Path) -> None:
    path = Path(path)

    data = {
        "version": notebook.version,
        "cells": [
            {
                "id": c.id,
                "type": c.type.value,
                "source": c.source,
                "output": c.output,
                "error": c.error,
                "execution_count": c.execution_count,
            }
            for c in notebook.cells
        ],
        "metadata": notebook.metadata,
    }

    path.write_text(json.dumps(data, indent=2) + "\n")
