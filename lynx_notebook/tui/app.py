from __future__ import annotations

from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, TextArea
from textual.widget import Widget

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import Cell, CellResult, CellType, Notebook
from lynx_notebook.tui.theme import build_css, style_editor


def _preview(source: str) -> str:
    first = next((line.strip() for line in source.splitlines() if line.strip()), "")
    head = first[:60]
    return "▸ " + head if head else "▸ (empty)"


class CodeCell(Widget):
    def __init__(self, cell: Cell, index: int) -> None:
        super().__init__(classes="cell code-cell")
        self.cell = cell
        self.index = index
        self._collapsed = False

    def compose(self) -> ComposeResult:
        self.editor = TextArea.code_editor(self.cell.source, classes="code-editor")
        style_editor(self.editor)

        self.result = Static("", classes="cell-result")
        self.result.visible = False

        self.bar = Static("", classes="cell-bar")
        self.bar.visible = False

        with Vertical(classes="cell-frame"):
            yield Static("×", classes="delete-btn")
            with Vertical(classes="cell-body"):
                yield self.editor
                yield self.result
            yield self.bar

    def get_source(self) -> str:
        return self.editor.text

    def update_from_result(self, result: CellResult) -> None:
        if result.output:
            self.result.update("\n".join("› " + line for line in result.output))
            self.result.set_class(True, "cell-output")
            self.result.set_class(False, "cell-error")
            self.result.visible = True
        elif result.error:
            lines = result.error.splitlines()
            head = ("✗ " + lines[0]) if lines else "✗ "
            rest = "\n".join(lines[1:])
            self.result.update(head + (("\n" + rest) if rest else ""))
            self.result.set_class(True, "cell-error")
            self.result.set_class(False, "cell-output")
            self.result.visible = True
        else:
            self.result.visible = False

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.set_class(collapsed, "collapsed")
        if collapsed:
            self.bar.visible = True
            self.bar.update(_preview(self.cell.source))
        if not collapsed:
            self.bar.visible = False
            self.editor.focus()

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def focus_body(self) -> None:
        self.editor.focus()


class InsertBar(Horizontal):
    def __init__(self, after_index: int) -> None:
        super().__init__(classes="insert-bar")
        self.after_index = after_index

    def compose(self) -> ComposeResult:
        yield Static("+", id=f"insert-{self.after_index}", classes="insert-btn")


class CellList(VerticalScroll):
    def __init__(self, notebook: Notebook, **kwargs) -> None:
        super().__init__(**kwargs)
        self.notebook = notebook
        self.cell_widgets: list[CodeCell] = []

    def compose(self) -> ComposeResult:
        for i, cell in enumerate(self.notebook.cells):
            widget = self._make_widget(cell, i)
            self.cell_widgets.append(widget)
            yield widget
            yield InsertBar(after_index=i)

        yield InsertBar(after_index=len(self.notebook.cells))

    def _make_widget(self, cell: Cell, index: int) -> CodeCell:
        return CodeCell(cell, index)


class NotebookApp(App):
    CSS = build_css()

    BINDINGS = [
        Binding("ctrl+enter", "run_cell", "Run cell", show=True),
        Binding("ctrl+shift+enter", "run_all", "Run all", show=True),
        Binding("ctrl+n", "insert_code", "New cell", show=True),
        Binding("ctrl+up", "prev_cell", "Previous cell", show=False),
        Binding("ctrl+down", "next_cell", "Next cell", show=False),
        Binding("ctrl+[", "collapse_cell", "Collapse cell", show=False),
        Binding("ctrl+]", "expand_cell", "Expand cell", show=False),
        Binding("ctrl+backspace", "delete_cell", "Delete cell", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(self, engine: NotebookEngine, notebook: Notebook, path=None) -> None:
        super().__init__()
        self.engine = engine
        self.notebook = notebook
        self.path = path
        self.focused_cell_index = 0

    def compose(self) -> ComposeResult:
        yield CellList(self.notebook, id="cell-list")
        yield Static("", id="app-status")

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        if event.widget.has_class("delete-btn"):
            cell = self._ancestor_cell(event.widget)
            if cell is not None:
                self._delete_cell_at(cell.index)
            return
        cell = self._ancestor_cell(event.widget)
        if cell is None:
            return
        self.focused_cell_index = cell.index
        if cell._collapsed:
            cell.toggle_collapsed()

    def _ancestor_cell(self, widget) -> CodeCell | None:
        node = widget
        while node is not None:
            if isinstance(node, CodeCell):
                return node
            node = node.parent
        return None

    @on(events.Click, ".insert-btn")
    def on_insert_press(self, event: events.Click) -> None:
        widget = event.widget
        if not widget or not widget.id:
            return
        try:
            index = int(widget.id.split("-")[1])
        except (IndexError, ValueError):
            return
        self._insert_cell(index)

    def action_insert_code(self) -> None:
        self._insert_cell(self.focused_cell_index + 1)

    def _insert_cell(self, index: int) -> None:
        self.notebook.add_cell(CellType.CODE, index=index)
        self._refresh_cells(after_focus=index)
        self._auto_save()

    def action_delete_cell(self) -> None:
        self._delete_cell_at(self.focused_cell_index)

    def _delete_cell_at(self, index: int) -> None:
        if not self.notebook.cells or not (0 <= index < len(self.notebook.cells)):
            return
        self.notebook.remove_cell(self.notebook.cells[index].id)
        new_index = min(index, max(0, len(self.notebook.cells) - 1))
        self._refresh_cells(after_focus=None if not self.notebook.cells else new_index)
        self.focused_cell_index = new_index
        self._auto_save()

    def _refresh_cells(self, after_focus: int | None = None) -> None:
        cell_list = self.query_one("#cell-list")
        cell_list.remove_children()
        cell_list.cell_widgets = []

        for i, cell in enumerate(self.notebook.cells):
            widget = cell_list._make_widget(cell, i)
            cell_list.cell_widgets.append(widget)
            cell_list.mount(widget)
            cell_list.mount(InsertBar(after_index=i))

        cell_list.mount(InsertBar(after_index=len(self.notebook.cells)))

        self._update_status()

        if after_focus is not None:
            self.call_after_refresh(self._focus_cell, after_focus)

    @property
    def cell_widgets(self) -> list[CodeCell]:
        return self.query_one("#cell-list").cell_widgets

    def _focus_cell(self, index: int) -> None:
        if 0 <= index < len(self.cell_widgets):
            self.focused_cell_index = index
            self.cell_widgets[index].focus_body()
            self._update_status()

    def _current_cell_widget(self) -> CodeCell | None:
        if 0 <= self.focused_cell_index < len(self.cell_widgets):
            return self.cell_widgets[self.focused_cell_index]
        return None

    def _sync_source(self, index: int | None = None) -> None:
        widget = self.cell_widgets[index] if index is not None else self._current_cell_widget()
        if widget is None:
            return
        widget.cell.source = widget.get_source()

    def action_run_cell(self) -> None:
        self._sync_source()
        widget = self._current_cell_widget()
        if widget is None:
            return
        result = self.engine.execute_cell(widget.cell, self.notebook)
        widget.update_from_result(result)
        self._auto_save()

    def action_run_all(self) -> None:
        for index, widget in enumerate(self.cell_widgets):
            self._sync_source(index)
            result = self.engine.execute_cell(widget.cell, self.notebook)
            widget.update_from_result(result)
        self.focused_cell_index = len(self.cell_widgets) - 1
        self._auto_save()

    def action_prev_cell(self) -> None:
        if self.focused_cell_index > 0:
            self.focused_cell_index -= 1
            self._focus_cell(self.focused_cell_index)

    def action_next_cell(self) -> None:
        if self.focused_cell_index < len(self.cell_widgets) - 1:
            self.focused_cell_index += 1
            self._focus_cell(self.focused_cell_index)

    def action_collapse_cell(self) -> None:
        widget = self._current_cell_widget()
        if widget is not None:
            widget.set_collapsed(True)

    def action_expand_cell(self) -> None:
        widget = self._current_cell_widget()
        if widget is not None:
            widget.set_collapsed(False)

    def action_quit(self) -> None:
        self._auto_save()
        self.exit()

    def _auto_save(self) -> None:
        if self.path is not None:
            self.engine.save(self.notebook, self.path)

    def on_mount(self) -> None:
        self.title = str(self.path) if self.path else "new notebook.lxnb"
        self._update_status()
        if self.notebook.cells:
            self._focus_cell(0)

    def _update_status(self) -> None:
        bar = self.query_one("#app-status", Static)
        path = self.path if self.path else "new notebook.lxnb"
        n = len(self.cell_widgets)
        current = f"cell {self.focused_cell_index + 1}/{n}" if n else "no cells"
        bar.update(f"{path}    {current}")
