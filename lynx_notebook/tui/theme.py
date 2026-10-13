from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Theming. Every color, spacing value and glyph lives in themes/default.json.
# To customise, copy that file to ~/.config/lynx-notebook/theme.json and keep
# only the keys you want to change (it is deep-merged over the defaults).
# Set LYNX_THEME=light|dark to override "mode" for one run.
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

DEFAULT_THEME_PATH = Path(__file__).parent / "themes" / "default.json"
USER_THEME_PATH = Path.home() / ".config" / "lynx-notebook" / "theme.json"

SYNTAX_KEYS = (
    "keyword", "string", "number", "comment", "function", "operator", "type", "boolean", "variable",
)


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _detect_mode() -> str:
    # COLORFGBG is "fg;bg" in terminals that set it; bg 7/15 means a light background.
    bg = os.environ.get("COLORFGBG", "").split(";")[-1]
    return "light" if bg in ("7", "15") else "dark"


@dataclass
class Theme:
    data: dict
    mode: str

    @property
    def colors(self) -> dict:
        return self.data["themes"][self.mode]

    @property
    def syntax(self) -> dict:
        return self.colors["syntax"]

    @property
    def spacing(self) -> dict:
        return self.data["spacing"]

    @property
    def glyphs(self) -> dict:
        return self.data["glyphs"]

    @property
    def border(self) -> dict:
        return self.data["border"]

    @property
    def name(self) -> str:
        return f"lynx-{self.mode}"

    def with_mode(self, mode: str) -> "Theme":
        return Theme(self.data, mode)

    def toggled(self) -> "Theme":
        return self.with_mode("light" if self.mode == "dark" else "dark")

    def css_variables(self) -> dict[str, str]:
        """Variables referenced as $lx-name in the stylesheet below."""
        colors = {k.replace("_", "-"): v for k, v in self.colors.items() if k != "syntax"}
        spacing = {k.replace("_", "-"): str(v) for k, v in self.spacing.items()}
        merged = {
            **colors,
            **spacing,
            "cell-border": self.border["cell"],
            "focus-border": self.border["focus"],
        }
        # Prefixed so they never collide with Textual's own $text, $surface, $error…
        return {f"lx-{k}": v for k, v in merged.items()}


def _validate(data: dict) -> None:
    for mode, colors in data["themes"].items():
        for key in ("bg", "surface", "text", "accent", "error"):
            if key not in colors:
                raise ValueError(f"theme '{mode}' is missing color '{key}'")
        for key in SYNTAX_KEYS:
            if key not in colors.get("syntax", {}):
                raise ValueError(f"theme '{mode}' is missing syntax color '{key}'")


def load_theme(user_path: Path | None = USER_THEME_PATH) -> Theme:
    """Bundled defaults, deep-merged with the user's file. A broken user file falls back."""
    data = json.loads(DEFAULT_THEME_PATH.read_text())
    if user_path is not None and user_path.exists():
        try:
            merged = _deep_merge(data, json.loads(user_path.read_text()))
            _validate(merged)
            data = merged
        except (ValueError, OSError) as exc:  # JSONDecodeError is a ValueError
            print(f"lynx-notebook: ignoring {user_path}: {exc}")

    mode = os.environ.get("LYNX_THEME") or data.get("mode", "dark")
    if mode == "auto":
        mode = _detect_mode()
    if mode not in data["themes"]:
        mode = "dark"
    return Theme(data, mode)


def _opaque(color: str, over: str) -> str:
    """Rich styles have no alpha: flatten #rrggbbaa onto a background color."""
    from textual.color import Color

    c = Color.parse(color)
    return Color.parse(over).blend(c.with_alpha(1.0), c.a).hex


def editor_theme(theme: Theme):
    """A TextAreaTheme built from the notebook colors."""
    from rich.style import Style
    from textual.widgets._text_area import TextAreaTheme

    c = theme.colors
    bg = c["surface"]
    return TextAreaTheme(
        name=theme.name,
        base_style=Style(color=c["text"], bgcolor=bg),
        gutter_style=Style(color=c["text_tertiary"], bgcolor=bg),
        cursor_style=Style(color=bg, bgcolor=c["accent"]),
        cursor_line_style=Style(bgcolor=_opaque(c["cursor_line"], bg)),
        cursor_line_gutter_style=Style(color=c["text_secondary"], bgcolor=_opaque(c["cursor_line"], bg)),
        selection_style=Style(bgcolor=_opaque(c["selection"], bg)),
        bracket_matching_style=Style(color=c["accent"], bold=True),
        syntax_styles={
            "keyword": Style(color=theme.syntax["keyword"]),
            "string": Style(color=theme.syntax["string"]),
            "number": Style(color=theme.syntax["number"]),
            "comment": Style(color=theme.syntax["comment"], italic=True),
            "function": Style(color=theme.syntax["function"]),
            "operator": Style(color=theme.syntax["operator"]),
            "type": Style(color=theme.syntax["type"]),
            "boolean": Style(color=theme.syntax["boolean"]),
            "variable": Style(color=theme.syntax["variable"]),
        },
    )


def style_editor(editor, theme: Theme) -> None:
    """Register the theme on an editor and select it."""
    editor.register_theme(editor_theme(theme))
    editor.theme = theme.name


# Rules reference $variables only (supplied by Theme.css_variables), no literals.
CSS = """
Screen {
    background: $lx-bg;
    color: $lx-text;
}

#cell-list {
    background: $lx-bg;
    padding: $lx-page-y $lx-page-x;
    overflow-y: auto;
    align-horizontal: center;
    scrollbar-size-vertical: 1;
    scrollbar-background: $lx-bg;
    scrollbar-color: $lx-border;
    scrollbar-color-hover: $lx-text-tertiary;
}

#app-status {
    dock: bottom;
    height: 1;
    padding: 0 $lx-page-x;
    background: $lx-bg;
    color: $lx-text-tertiary;
}

.cell {
    height: auto;
    width: 100%;
    max-width: $lx-max-width;
}

.cell-frame {
    border: $lx-cell-border $lx-bg;
    background: $lx-surface;
    padding: 0 $lx-cell-pad-x;
    height: auto;
}

.cell:hover .cell-frame {
    border: $lx-cell-border $lx-border;
}

.cell:focus-within .cell-frame {
    border: $lx-focus-border $lx-border-focus;
    background: $lx-surface-focus;
}

.markdown-cell .cell-frame {
    background: $lx-bg;
}

.markdown-cell:focus-within .cell-frame {
    border: $lx-focus-border $lx-accent-md;
    background: $lx-surface-focus;
}

.delete-btn {
    dock: right;
    width: 1;
    height: auto;
    background: transparent;
    color: $lx-text-tertiary;
    visibility: hidden;
}

.cell:hover .delete-btn {
    visibility: visible;
}

.delete-btn:hover {
    color: $lx-error;
}

.code-editor, .md-editor {
    border: none;
    height: auto;
    min-height: $lx-editor-min-height;
    padding: 0;
    background: transparent;
}

.code-editor:focus, .md-editor:focus {
    background-tint: transparent;
}

.md-view {
    height: auto;
    margin: 0;
    padding: 0;
    background: transparent;
    color: $lx-text;
}

.cell-result {
    height: auto;
    margin: 1 0 0 0;
}

.cell-output {
    color: $lx-output;
}

.cell-error {
    color: $lx-error;
}

.cell-body {
    height: auto;
}

.cell.collapsed .cell-body {
    display: none;
}

.cell-bar {
    height: 1;
    color: $lx-text-secondary;
    background: transparent;
}

.cell-bar:hover {
    color: $lx-accent;
}

.insert-bar {
    height: $lx-cell-gap;
    width: 100%;
    max-width: $lx-max-width;
    align-horizontal: center;
}

.insert-btn {
    background: transparent;
    color: $lx-bg;
    border: none;
    height: 1;
    padding: 0 1;
}

.insert-bar:hover .insert-btn {
    background: $lx-surface-focus;
    color: $lx-accent;
}
"""
