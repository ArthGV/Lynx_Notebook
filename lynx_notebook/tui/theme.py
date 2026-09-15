from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# All colors in one place. Edit here and the whole TUI follows.
# ─────────────────────────────────────────────────────────────────────────────

BG_COLOR = "#000000"
CELL_BG = "#000000"
TEXT = "#ffffff"
MUTED = "#ffffff"
GUTTER = "#ffffff"
BORDER = "#ffffff"
ACCENT = "#ffffff"
ERROR = "#ec8c8c"
OUTPUT = "#96B6DA"

# ─────────────────────────────────────────────────────────────────────────────
# Terminal font size is set in your terminal emulator (Cmd+ / Cmd−),
# not from the app. The knobs below control density / spacing.
# ─────────────────────────────────────────────────────────────────────────────
CELL_MARGIN_BOTTOM = 1
EDITOR_MIN_HEIGHT = 1


def editor_theme():
    """A TextAreaTheme matching the notebook colors (no monokai brown)."""
    from rich.style import Style
    from textual.widgets._text_area import TextAreaTheme

    return TextAreaTheme(
        name="lynx-dark",
        base_style=Style(color=TEXT, bgcolor=CELL_BG),
        gutter_style=Style(color=GUTTER, bgcolor=CELL_BG),
        cursor_style=Style(color=BG_COLOR, bgcolor=ACCENT, bold=True),
        cursor_line_gutter_style=Style(color=ACCENT, bgcolor=CELL_BG),
        cursor_line_style=Style(bgcolor="#1b2028"),
        selection_style=Style(bgcolor="#2b3850"),
        bracket_matching_style=Style(color=ACCENT, bold=True),
    )


def style_editor(editor) -> None:
    """Register the lynx theme on an editor and select it. Runs once per editor."""
    editor.register_theme(editor_theme())
    editor.theme = "lynx-dark"


def build_css() -> str:
    return f"""
$bg: {BG_COLOR};
$cell-bg: {CELL_BG};
$text: {TEXT};
$muted: {MUTED};
$gutter: {GUTTER};
$border: {BORDER};
$accent: {ACCENT};
$error: {ERROR};
$output: {OUTPUT};

Screen {{
    background: $bg;
    color: $text;
}}

#cell-list {{
    background: $bg;
    padding: 1 2;
    overflow-y: auto;
}}

#app-status {{
    dock: bottom;
    height: 1;
    padding: 0 2;
    background: $bg;
    color: $muted;
}}

.code-cell {{
    height: auto;
    margin: 0 0 {CELL_MARGIN_BOTTOM} 0;
}}

.cell-frame {{
    border: round $border;
    background: $cell-bg;
    height: auto;
}}

.delete-btn {{
    dock: right;
    width: 1;
    height: auto;
    background: transparent;
    color: $muted;
}}

.delete-btn:hover {{
    color: $error;
}}

.code-editor {{
    border: none;
    height: auto;
    min-height: {EDITOR_MIN_HEIGHT};
}}

.cell-output {{
    color: $output;
    padding: 0 0 0 1;
    height: auto;
}}

.cell-error {{
    color: $error;
    padding: 0 0 0 1;
    height: auto;
}}

.cell-body {{
    height: auto;
}}

.cell.collapsed .cell-body {{
    display: none;
}}

.cell-bar {{
    height: 1;
    color: $muted;
    background: transparent;
}}

.cell-bar:hover {{
    color: $accent;
}}

.insert-bar {{
    height: 1;
    align-horizontal: center;
}}

.insert-btn {{
    background: transparent;
    color: $muted;
    border: none;
    height: 1;
    padding: 0 1;
}}

.insert-bar:hover .insert-btn {{
    background: #1b2028;
    color: $text;
}}
"""