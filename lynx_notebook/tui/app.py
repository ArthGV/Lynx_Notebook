from __future__ import annotations

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Markdown, Static, TextArea
from textual.widget import Widget

from lynx_notebook.engine import NotebookEngine
from lynx_notebook.models import Cell, CellResult, CellType, Notebook
from lynx_notebook.tui.theme import CSS as THEME_CSS, Theme, load_theme, style_editor


def _preview(source: str, theme: Theme) -> str:
    first = next((line.strip() for line in source.splitlines() if line.strip()), "")
    head = first[: theme.glyphs["preview_len"]]
    marker = theme.glyphs["collapsed"]
    return f"{marker} {head}" if head else f"{marker} (empty)"


def _railed(lines: list[str], rail: str, color: str) -> Text:
    text = Text()
    for i, line in enumerate(lines):
        if i:
            text.append("\n")
        text.append(rail + " ", style=color)
        text.append(line)
    return text


class CodeCell(Widget):
    KIND = "code"

    def __init__(self, cell: Cell, index: int, theme: Theme) -> None:
        super().__init__(classes=f"cell {self.KIND}-cell")
        self.cell = cell
        self.index = index
        self.nb_theme = theme
        self._collapsed = False

    def make_editor(self) -> TextArea:
        return TextArea.code_editor(self.cell.source, classes="code-editor")

    def compose(self) -> ComposeResult:
        self.editor = self.make_editor()
        style_editor(self.editor, self.nb_theme)

        self.result = Static("", classes="cell-result")
        self.result.visible = False

        self.bar = Static("", classes="cell-bar")
        self.bar.visible = False

        with Vertical(classes="cell-frame"):
            yield Static(self.nb_theme.glyphs["delete"], classes="delete-btn")
            with Vertical(classes="cell-body"):
                yield from self.compose_body()
                yield self.result
            yield self.bar

    def compose_body(self) -> ComposeResult:
        yield self.editor

    def get_source(self) -> str:
        return self.editor.text

    def restyle(self, theme: Theme) -> None:
        self.nb_theme = theme
        style_editor(self.editor, theme)

    def update_from_result(self, result: CellResult) -> None:
        glyphs, colors = self.nb_theme.glyphs, self.nb_theme.colors
        if result.output:
            self.result.update(_railed(result.output, glyphs["output_rail"], colors["border_focus"]))
            self.result.set_class(True, "cell-output")
            self.result.set_class(False, "cell-error")
            self.result.visible = True
        elif result.error:
            self.result.update(_railed(result.error.splitlines() or [""], glyphs["error_rail"], colors["error"]))
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
            self.bar.update(_preview(self.get_source(), self.nb_theme))
        else:
            self.bar.visible = False
            self.focus_body()

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def focus_body(self) -> None:
        self.editor.focus()

    def activate(self) -> None:
        """Called when the user clicks the cell."""
        if self._collapsed:
            self.toggle_collapsed()

    def run_action(self) -> bool:
        """Return True if the cell needs the engine to execute it."""
        return True


class MarkdownCell(CodeCell):
    """Rendered markdown when idle; click or focus to edit, blur to render."""

    KIND = "markdown"

    def __init__(self, cell: Cell, index: int, theme: Theme) -> None:
        super().__init__(cell, index, theme)
        self.editing = not cell.source.strip()

    def make_editor(self) -> TextArea:
        return TextArea(self.cell.source, classes="md-editor")

    def compose_body(self) -> ComposeResult:
        self.view = Markdown(self.cell.source, classes="md-view")
        yield self.editor
        yield self.view

    def on_mount(self) -> None:
        self._apply_mode()

    def _apply_mode(self) -> None:
        self.editor.display = self.editing
        self.view.display = not self.editing

    def begin_edit(self) -> None:
        self.editing = True
        self._apply_mode()
        self.editor.focus()

    def show_view(self) -> None:
        self.cell.source = self.editor.text
        self.editing = False
        self.view.update(self.cell.source)
        self._apply_mode()

    def focus_body(self) -> None:
        self.begin_edit()

    def activate(self) -> None:
        super().activate()
        if not self._collapsed and not self.editing:
            self.begin_edit()

    def run_action(self) -> bool:
        self.show_view()
        return False

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        if event.widget is self.editor and self.editing and self.editor.text.strip():
            self.show_view()


class InsertBar(Horizontal):
    def __init__(self, after_index: int, glyph: str = "+") -> None:
        super().__init__(classes="insert-bar")
        self.after_index = after_index
        self.glyph = glyph

    def compose(self) -> ComposeResult:
        yield Static(self.glyph, id=f"insert-{self.after_index}", classes="insert-btn")


class CellList(VerticalScroll):
    def __init__(self, notebook: Notebook, theme: Theme, **kwargs) -> None:
        super().__init__(**kwargs)
        self.notebook = notebook
        self.nb_theme = theme
        self.cell_widgets: list[CodeCell] = []

    def compose(self) -> ComposeResult:
        for i, cell in enumerate(self.notebook.cells):
            widget = self._make_widget(cell, i)
            self.cell_widgets.append(widget)
            yield widget
            yield self.make_insert_bar(i)

        yield self.make_insert_bar(len(self.notebook.cells))

    def make_insert_bar(self, index: int) -> InsertBar:
        return InsertBar(after_index=index, glyph=self.nb_theme.glyphs["insert"])

    def _make_widget(self, cell: Cell, index: int) -> CodeCell:
        cls = MarkdownCell if cell.type == CellType.MARKDOWN else CodeCell
        return cls(cell, index, self.nb_theme)


class NotebookApp(App):
    CSS = THEME_CSS

    BINDINGS = [
        Binding("ctrl+enter", "run_cell", "Run cell", show=True),
        Binding("ctrl+shift+enter", "run_all", "Run all", show=True),
        Binding("ctrl+n", "insert_code", "New cell", show=True),
        Binding("f2", "insert_markdown", "New markdown cell", show=True),
        Binding("ctrl+t", "toggle_theme", "Light/dark", show=True),
        Binding("ctrl+up", "prev_cell", "Previous cell", show=False),
        Binding("ctrl+down", "next_cell", "Next cell", show=False),
        Binding("ctrl+[", "collapse_cell", "Collapse cell", show=False),
        Binding("ctrl+]", "expand_cell", "Expand cell", show=False),
        Binding("ctrl+backspace", "delete_cell", "Delete cell", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(
        self, engine: NotebookEngine, notebook: Notebook, path=None, theme: Theme | None = None
    ) -> None:
        self.nb_theme = theme or load_theme()
        super().__init__()
        self.engine = engine
        self.notebook = notebook
        self.path = path
        self.focused_cell_index = 0

    def get_css_variables(self) -> dict[str, str]:
        return {**super().get_css_variables(), **self.nb_theme.css_variables()}

    def compose(self) -> ComposeResult:
        yield CellList(self.notebook, self.nb_theme, id="cell-list")
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
        cell.activate()

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

    def action_insert_markdown(self) -> None:
        self._insert_cell(self.focused_cell_index + 1, CellType.MARKDOWN)

    def _insert_cell(self, index: int, cell_type: CellType = CellType.CODE) -> None:
        self.notebook.add_cell(cell_type, index=index)
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
            cell_list.mount(cell_list.make_insert_bar(i))

        cell_list.mount(cell_list.make_insert_bar(len(self.notebook.cells)))

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
        if widget.run_action():
            result = self.engine.execute_cell(widget.cell, self.notebook)
            widget.update_from_result(result)
        self._auto_save()

    def action_run_all(self) -> None:
        for index, widget in enumerate(self.cell_widgets):
            self._sync_source(index)
            if widget.run_action():
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

    def action_toggle_theme(self) -> None:
        self._apply_theme(self.nb_theme.toggled())

    def _apply_theme(self, theme: Theme) -> None:
        self.nb_theme = theme
        self.theme = "textual-light" if theme.mode == "light" else "textual-dark"
        self.refresh_css()
        cell_list = self.query_one("#cell-list")
        cell_list.nb_theme = theme
        for widget in self.cell_widgets:
            widget.restyle(theme)
        self._update_status()

    def action_quit(self) -> None:
        self._auto_save()
        self.exit()

    def _auto_save(self) -> None:
        if self.path is not None:
            self.engine.save(self.notebook, self.path)

    def on_mount(self) -> None:
        self.title = str(self.path) if self.path else "new notebook.lxnb"
        self.theme = "textual-light" if self.nb_theme.mode == "light" else "textual-dark"
        self._update_status()
        if self.notebook.cells:
            self._focus_cell(0)

    def _update_status(self) -> None:
        bar = self.query_one("#app-status", Static)
        path = self.path if self.path else "new notebook.lxnb"
        n = len(self.cell_widgets)
        current = f"cell {self.focused_cell_index + 1}/{n}" if n else "no cells"
        bar.update(f"{path}    {current}")
