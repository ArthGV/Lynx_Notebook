from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import Any

from src.main import run
from src.runtime.environment import Environment

from lynx_notebook.models import CellResult


def execute_cell_source(source: str, env: Environment) -> CellResult:
    buf = io.StringIO()
    error: str | None = None
    try:
        with redirect_stdout(buf):
            run(source, env)
    except Exception as e:
        error = str(e)

    output = buf.getvalue().splitlines()
    return CellResult(output=output, error=error, execution_count=0)
