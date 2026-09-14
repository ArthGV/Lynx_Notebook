from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import CellType


def test_execute_cell_captures_output(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    cell = notebook.add_cell(CellType.CODE, ">> 1 + 1")

    result = engine.execute_cell(cell, notebook)

    assert result.error is None
    assert result.output == ["2"]
    assert cell.output == ["2"]
    assert cell.execution_count == 1
    assert result.execution_count == 1


def test_execution_count_increments(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    c1 = notebook.add_cell(CellType.CODE, ">> 1")
    c2 = notebook.add_cell(CellType.CODE, ">> 2")

    engine.execute_cell(c1, notebook)
    engine.execute_cell(c2, notebook)

    assert c1.execution_count == 1
    assert c2.execution_count == 2


def test_shared_environment_across_cells(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    c1 = notebook.add_cell(CellType.CODE, "x : 42")
    c2 = notebook.add_cell(CellType.CODE, ">> x + 1")

    engine.execute_cell(c1, notebook)
    result = engine.execute_cell(c2, notebook)

    assert result.error is None
    assert result.output == ["43"]


def test_execute_cell_error_recorded(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    cell = notebook.add_cell(CellType.CODE, ">> missing_var")

    result = engine.execute_cell(cell, notebook)

    assert result.output == []
    assert result.error is not None
    assert "missing_var" in result.error
    assert cell.error is not None


def test_execute_all_stops_are_sequential(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    notebook.add_cell(CellType.CODE, "x : 10")
    notebook.add_cell(CellType.CODE, ">> x")
    notebook.add_cell(CellType.CODE, ">> x + 1")

    results = engine.execute_all(notebook)

    assert results[1].output == ["10"]
    assert results[2].output == ["11"]


def test_save_load_round_trip(tmp_path):
    engine = NotebookEngine()
    notebook = engine.new_notebook()
    code_cell = notebook.add_cell(CellType.CODE, ">> 42")
    md_cell = notebook.add_cell(CellType.MARKDOWN, "# Title\nbody")
    engine.execute_cell(code_cell, notebook)

    path = tmp_path / "nb.lxnb"
    engine.save(notebook, path)

    loaded = engine.load(path)
    assert len(loaded.cells) == 2
    assert loaded.cells[0].source == ">> 42"
    assert loaded.cells[0].output == ["42"]
    assert loaded.cells[1].type == CellType.MARKDOWN
    assert loaded.cells[1].source == "# Title\nbody"