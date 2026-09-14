from __future__ import annotations

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Markdown, Static, TextArea
from textual.widget import Widget

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import Cell, CellResult, CellType, Notebook
from lynx_notebook.tui.theme import build_css


class CodeCell(Widget):
    def __init__(self, cell: Cell, index: int) -> None:
        super().__init__()
        self.cell = cell
        self.index = index

    def compose(self) -> ComposeResult:
        self.editor = TextArea.code_editor(self.cell.source, classes="code-editor")

        self.output_text = Static("", classes="cell-output")
        self.output_text.visible = False

        self.error_text = Static("", classes="cell-error")
        self.error_text.visible = False

        with Vertical(classes="cell"):
            yield self.editor
            yield self.output_text
            yield self.error_text

    def get_source(self) -> str:
        return self.editor.text

    def update_from_result(self, result: CellResult) -> None:
        if result.output:
            self.output_text.update("\n".join(result.output))
            self.output_text.visible = True
        else:
            self.output_text.visible = False

        if result.error:
            self.error_text.update(result.error)
            self.error_text.visible = True
        else:
            self.error_text.visible = False

    def focus_editor(self) -> None:
        self.editor.focus()


class MarkdownCell(Widget):
    def __init__(self, cell: Cell, index: int) -> None:
        super().__init__()
        self.cell = cell
        self.index = index
        self._editing = False

    def compose(self) -> ComposeResult:
        self.editor = TextArea.code_editor(self.cell.source, classes="md-editor")
        self.editor.visible = False

        self.renderer = Markdown(self.cell.source, classes="md-render")
        self.renderer.styles.padding = (1, 2)

        with Vertical(classes="cell"):
            yield self.editor
            yield self.renderer

    def get_source(self) -> str:
        return self.editor.text

    def toggle_edit(self) -> None:
        self._editing = not self._editing
        self.editor.visible = self._editing
        self.renderer.visible = not self._editing
        if self._editing:
            self.editor.load_text(self.cell.source)
            self.editor.focus()
        else:
            self.cell.source = self.editor.text
            self.renderer.update(self.editor.text)

    def focus_editor(self) -> None:
        self.editor.focus()


class InsertBar(Widget):
    def __init__(self, after_index: int) -> None:
        super().__init__()
        self.after_index = after_index

    def compose(self) -> ComposeResult:
        yield Button("+", id=f"insert-{self.after_index}", classes="insert-btn")


class CellList(VerticalScroll):
    def __init__(self, notebook: Notebook, **kwargs) -> None:
        super().__init__(**kwargs)
        self.notebook = notebook
        self.cell_widgets: list[CodeCell | MarkdownCell] = []

    def compose(self) -> ComposeResult:
        for i, cell in enumerate(self.notebook.cells):
            widget = self._make_widget(cell, i)
            self.cell_widgets.append(widget)
            yield widget
            yield InsertBar(after_index=i)

        yield InsertBar(after_index=len(self.notebook.cells))

    def _make_widget(self, cell: Cell, index: int) -> CodeCell | MarkdownCell:
        if cell.type == CellType.CODE:
            return CodeCell(cell, index)
        return MarkdownCell(cell, index)


class NotebookApp(App):
    CSS = build_css()

    BINDINGS = [
        Binding("ctrl+enter", "run_cell", "Run cell", show=True),
        Binding("ctrl+shift+enter", "run_all", "Run all", show=True),
        Binding("ctrl+n", "insert_code", "New code cell", show=True),
        Binding("ctrl+m", "insert_markdown", "New md cell", show=True),
        Binding("ctrl+up", "prev_cell", "Previous cell", show=False),
        Binding("ctrl+down", "next_cell", "Next cell", show=False),
        Binding("ctrl+backspace", "delete_cell", "Delete cell", show=True),
        Binding("ctrl+e", "toggle_markdown_edit", "Edit md cell", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(self, engine: NotebookEngine, notebook: Notebook, path=None) -> None:
        super().__init__()
        self.engine = engine
        self.notebook = notebook
        self.path = path
        self.focused_cell_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield CellList(self.notebook, id="cell-list")
        yield Footer()

    @on(Button.Pressed, ".insert-btn")
    def on_insert_press(self, event: Button.Pressed) -> None:
        try:
            index = int(event.button.id.split("-")[1])
        except (IndexError, ValueError):
            return
        self._insert_cell(CellType.CODE, index)

    def action_insert_code(self) -> None:
        self._insert_cell(CellType.CODE, self.focused_cell_index + 1)

    def action_insert_markdown(self) -> None:
        self._insert_cell(CellType.MARKDOWN, self.focused_cell_index + 1)

    def _insert_cell(self, cell_type: CellType, index: int) -> None:
        self.notebook.add_cell(cell_type, index=index)
        self._refresh_cells(after_focus=index)
        self._auto_save()

    def action_delete_cell(self) -> None:
        if not self.notebook.cells:
            return
        idx = min(self.focused_cell_index, len(self.notebook.cells) - 1)
        cell = self.notebook.cells[idx]
        self.notebook.remove_cell(cell.id)
        new_index = min(idx, max(0, len(self.notebook.cells) - 1))
        self._refresh_cells(after_focus=None if not self.notebook.cells else new_index)
        self.focused_cell_index = new_index
        self._auto_save()

    def action_toggle_markdown_edit(self) -> None:
        widget = self._current_cell_widget()
        if isinstance(widget, MarkdownCell):
            widget.toggle_edit()

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

        if after_focus is not None:
            self.call_after_refresh(self._focus_cell, after_focus)

    @property
    def cell_widgets(self) -> list[CodeCell | MarkdownCell]:
        return self.query_one("#cell-list").cell_widgets

    def _focus_cell(self, index: int) -> None:
        if 0 <= index < len(self.cell_widgets):
            self.focused_cell_index = index
            widget = self.cell_widgets[index]
            if isinstance(widget, CodeCell) or (isinstance(widget, MarkdownCell) and widget._editing):
                widget.focus_editor()

    def _current_cell_widget(self) -> CodeCell | MarkdownCell | None:
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
        if widget is None or widget.cell.type != CellType.CODE:
            return
        result = self.engine.execute_cell(widget.cell, self.notebook)
        widget.update_from_result(result)
        self._auto_save()

    def action_run_all(self) -> None:
        for index, widget in enumerate(self.cell_widgets):
            self._sync_source(index)
            if widget.cell.type == CellType.CODE:
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

    def action_quit(self) -> None:
        self._auto_save()
        self.exit()

    def _auto_save(self) -> None:
        if self.path is not None:
            self.engine.save(self.notebook, self.path)

    def on_mount(self) -> None:
        self.title = str(self.path) if self.path else "new notebook.lxnb"
        if self.notebook.cells:
            self._focus_cell(0)