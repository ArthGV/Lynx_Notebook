import asyncio

import pytest
from textual import events
from textual.widgets import Button, Static

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import CellType
from lynx_notebook.tui.app import CodeCell, NotebookApp


def _app(path=None):
    engine = NotebookEngine()
    nb = engine.new_notebook()
    nb.add_cell(CellType.CODE, ">> 1")
    nb.add_cell(CellType.CODE, ">> 2")
    nb.add_cell(CellType.CODE, ">> 3")
    return NotebookApp(engine=engine, notebook=nb, path=path)


def _click(widget):
    return events.Click(
        x=0, y=0, delta_x=0, delta_y=0, button=0,
        shift=False, meta=False, ctrl=False, widget=widget,
    )


@pytest.mark.asyncio
async def test_app_composes_cells():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.cell_widgets) == 3
        assert all(isinstance(w, CodeCell) for w in app.cell_widgets)


@pytest.mark.asyncio
async def test_run_cell_shows_output():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        first = app.cell_widgets[0]
        app.action_run_cell()
        await pilot.pause()
        assert first.result.visible
        assert str(first.result.render()) == "› 1"
        assert first.cell.output == ["1"]


@pytest.mark.asyncio
async def test_run_all_executes_each_code_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_run_all()
        await pilot.pause()
        outs = [w.cell.output for w in app.cell_widgets]
        assert outs == [["1"], ["2"], ["3"]]


@pytest.mark.asyncio
async def test_insert_and_delete_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_insert_code()
        await pilot.pause()
        await pilot.pause()
        assert len(app.cell_widgets) == 4

        app.focused_cell_index = 1
        app.action_delete_cell()
        await pilot.pause()
        assert len(app.cell_widgets) == 3
        assert [w.cell.type.value for w in app.cell_widgets] == ["code", "code", "code"]


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


@pytest.mark.asyncio
async def test_editor_uses_dark_theme():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        editor = app.cell_widgets[0].editor
        assert editor.theme == "lynx-dark"


@pytest.mark.asyncio
async def test_editor_height_follows_content():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        code = app.cell_widgets[0]
        code.editor.load_text(">> 1\n>> 2\n>> 3")
        await pilot.pause()
        await pilot.pause()
        assert code.editor.size.height == 3


@pytest.mark.asyncio
async def test_collapse_and_expand_code_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        code = app.cell_widgets[0]
        code.set_collapsed(True)
        await pilot.pause()
        assert "collapsed" in code.classes
        assert code.bar.visible
        assert str(code.bar.render()) == "▸ >> 1"
        assert not code.query_one(".cell-body").display
        code.set_collapsed(False)
        await pilot.pause()
        assert "collapsed" not in code.classes
        assert not code.bar.visible
        assert code.query_one(".cell-body").display


@pytest.mark.asyncio
async def test_click_collapsed_cell_expands_it():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        code = app.cell_widgets[0]
        code.set_collapsed(True)
        app.on_click(_click(code.bar))
        await pilot.pause()
        assert not code._collapsed


@pytest.mark.asyncio
async def test_click_on_status_bar_does_not_change_focus():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.query_one("#app-status")
        app.on_click(_click(status))
        await pilot.pause()
        assert app.focused_cell_index == 0


@pytest.mark.asyncio
async def test_cells_have_delete_button():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.cell_widgets) == 3
        for cell in app.cell_widgets:
            btn = cell.query_one(".delete-btn")
            assert isinstance(btn, Static)
            assert "×" in str(btn.render())


@pytest.mark.asyncio
async def test_click_delete_button_deletes_cell():
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        cell = app.cell_widgets[1]
        btn = cell.query_one(".delete-btn")
        app.on_click(_click(btn))
        await pilot.pause()
        await pilot.pause()
        assert len(app.cell_widgets) == 2