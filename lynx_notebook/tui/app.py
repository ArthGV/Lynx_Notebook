from __future__ import annotations

from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Markdown, Static, TextArea
from textual.widget import Widget

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import Cell, CellResult, CellType, Notebook
from lynx_notebook.tui.theme import build_css, style_editor


def _preview(source: str, label: str | None = None) -> str:
    first = next((line.strip() for line in source.splitlines() if line.strip()), "")
    head = first[:60]
    bits = [lbl for lbl in [label, head] if lbl]
    return "▸ " + " / ".join(bits) if bits else "▸ (empty)"


class CodeCell(Widget):
    def __init__(self, cell: Cell, index: int) -> None:
        super().__init__(classes="cell")
        self.cell = cell
        self.index = index
        self._collapsed = False

    def compose(self) -> ComposeResult:
        self.editor = TextArea.code_editor(self.cell.source, classes="code-editor")
        style_editor(self.editor)

        self.output_text = Static("", classes="cell-output")
        self.output_text.visible = False

        self.error_text = Static("", classes="cell-error")
        self.error_text.visible = False

        self.bar = Static("", classes="cell-bar")
        self.bar.visible = False

        yield self.bar
        with Vertical(classes="cell-body"):
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


class MarkdownCell(Widget):
    def __init__(self, cell: Cell, index: int) -> None:
        super().__init__(classes="cell")
        self.cell = cell
        self.index = index
        self._editing = False
        self._collapsed = False

    def compose(self) -> ComposeResult:
        self.editor = TextArea.code_editor(self.cell.source, classes="md-editor")
        style_editor(self.editor)
        self.editor.visible = False

        self.renderer = Markdown(self.cell.source, classes="md-render")
        self.renderer.styles.padding = (1, 1)
        self.renderer.can_focus = True

        self.bar = Static("", classes="cell-bar")
        self.bar.visible = False
        self.bar.can_focus = True

        yield self.bar
        with Vertical(classes="cell-body"):
            yield self.editor
            yield self.renderer

    def get_source(self) -> str:
        return self.editor.text

    def enter_edit(self) -> None:
        self._editing = True
        self.editor.load_text(self.cell.source)
        self.editor.visible = True
        self.renderer.visible = False
        self.editor.focus()

    def exit_edit(self) -> None:
        self._editing = False
        self.cell.source = self.editor.text
        self.renderer.update(self.editor.text)
        self.editor.visible = False
        self.renderer.visible = True
        self.renderer.focus()

    def toggle_edit(self) -> None:
        (self.exit_edit if self._editing else self.enter_edit)()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.set_class(collapsed, "collapsed")
        if collapsed:
            self._editing = False
            self.editor.visible = False
            self.renderer.visible = True
            self.bar.visible = True
            self.bar.update(_preview(self.cell.source, label="md"))
            self.bar.focus()
        else:
            self.bar.visible = False
            self.renderer.focus()

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def focus_body(self) -> None:
        if self._collapsed:
            self.bar.focus()
        elif self._editing:
            self.editor.focus()
        else:
            self.renderer.focus()


class InsertBar(Widget):
    def __init__(self, after_index: int) -> None:
        super().__init__(classes="insert-bar")
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
        Binding("ctrl+e", "toggle_markdown_edit", "Edit md cell", show=True),
        Binding("ctrl+[", "collapse_cell", "Collapse cell", show=False),
        Binding("ctrl+]", "expand_cell", "Expand cell", show=False),
        Binding("escape", "exit_markdown_edit", "Finish md edit", show=False),
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
        yield Header()
        yield CellList(self.notebook, id="cell-list")
        yield Footer()

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        cell = self._ancestor_cell(event.widget)
        if cell is None:
            return
        self.focused_cell_index = cell.index
        if cell._collapsed:
            cell.toggle_collapsed()
            return
        if isinstance(cell, MarkdownCell) and not cell._editing:
            cell.enter_edit()

    def _ancestor_cell(self, widget) -> CodeCell | MarkdownCell | None:
        node: Widget | None = widget
        while node is not None:
            if isinstance(node, (CodeCell, MarkdownCell)):
                return node
            node = node.parent
        return None

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
            self.cell_widgets[index].focus_body()

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

    def action_toggle_markdown_edit(self) -> None:
        widget = self._current_cell_widget()
        if isinstance(widget, MarkdownCell):
            widget.toggle_edit()

    def action_exit_markdown_edit(self) -> None:
        widget = self._current_cell_widget()
        if isinstance(widget, MarkdownCell) and widget._editing:
            widget.exit_edit()

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
        if self.notebook.cells:
            self._focus_cell(0)