import asyncio

import pytest

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import CellType
from lynx_notebook.tui.app import NotebookApp


def _app(path=None):
    engine = NotebookEngine()
    nb = engine.new_notebook()
    nb.add_cell(CellType.CODE, ">> 1")
    nb.add_cell(CellType.MARKDOWN, "# Title\nbody")
    nb.add_cell(CellType.CODE, ">> 2")
    return NotebookApp(engine=engine, notebook=nb, path=path)


@pytest.mark.asyncio
async def test_app_composes_cells():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.cell_widgets) == 3
        assert app.cell_widgets[0].cell.type == CellType.CODE
        assert app.cell_widgets[1].cell.type == CellType.MARKDOWN


@pytest.mark.asyncio
async def test_run_cell_shows_output():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        first = app.cell_widgets[0]
        app.action_run_cell()
        await pilot.pause()
        assert first.output_text.visible
        assert str(first.output_text.render()) == "1"
        assert first.cell.output == ["1"]


@pytest.mark.asyncio
async def test_run_all_executes_each_code_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_run_all()
        await pilot.pause()
        outs = [w.cell.output for w in app.cell_widgets]
        assert outs == [["1"], [], ["2"]]


@pytest.mark.asyncio
async def test_insert_and_delete_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_insert_markdown()
        await pilot.pause()
        await pilot.pause()
        assert [w.cell.type.value for w in app.cell_widgets] == [
            "code", "markdown", "markdown", "code",
        ]

        app.focused_cell_index = 1
        app.action_delete_cell()
        await pilot.pause()
        assert [w.cell.type.value for w in app.cell_widgets] == [
            "code", "markdown", "code",
        ]


@pytest.mark.asyncio
async def test_autosave_on_quit(tmp_path):
    path = tmp_path / "nb.lxnb"
    app = _app(path=path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_run_cell()
        await pilot.pause()
        app.action_quit()
        await pilot.pause()

    assert path.exists()
    content = path.read_text()
    assert ">> 1" in content