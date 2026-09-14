from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# All colors in one place. Edit here and the whole TUI follows.
# ─────────────────────────────────────────────────────────────────────────────

BG_COLOR = "#0f1419"
SECONDARY_BG = "#1a1f29"
CODE_BORDER = "#3b4654"
FOCUS_ACCENT = "#58a6ff"
MD_BORDER = "#2d5c8a"
CODE_TEXT = "#e6edf3"
MD_TEXT = "#c9d4e0"
ACCENT = "#58a6ff"
ERROR = "#ff5555"
OUTPUT_TEXT = "#a8b3c0"
INSERT_ZONE = "#303a48"
OUTPUT_BG = "#12181f"
HEADER_BG = "#161b22"
HEADER_TEXT = "#e6edf3"

# native color (raw user text, e.g. in the markdown editor)
MD_EDIT_TEXT = "#e6edf3"
MD_EDIT_BG = "#141b24"
MD_EDIT_BORDER = "#1d2e45"


def build_css(app_css: str = "") -> str:
    return f"""
$bg: {BG_COLOR};
$secondary-bg: {SECONDARY_BG};
$code-border: {CODE_BORDER};
$focus-accent: {FOCUS_ACCENT};
$md-border: {MD_BORDER};
$code-text: {CODE_TEXT};
$md-text: {MD_TEXT};
$accent: {ACCENT};
$error: {ERROR};
$output-text: {OUTPUT_TEXT};
$insert-zone: {INSERT_ZONE};
$output-bg: {OUTPUT_BG};
$header-bg: {HEADER_BG};
$header-text: {HEADER_TEXT};
$md-edit-text: {MD_EDIT_TEXT};
$md-edit-bg: {MD_EDIT_BG};
$md-edit-border: {MD_EDIT_BORDER};

Screen {{
    background: $bg;
    color: $code-text;
}}

#header {{
    background: $header-bg;
    color: $header-text;
    height: 1;
    dock: top;
}}

#cell-list {{
    background: $bg;
    padding: 1 2;
    overflow-y: auto;
}}

.insert-btn {{
    background: transparent;
    color: $insert-zone;
    border: none;
    width: 100%;
    height: 1;
    text-align: center;
}}

.insert-btn:hover {{
    color: $accent;
    background: $secondary-bg;
}}

.code-editor {{
    border: solid $code-border;
    background: $bg;
    color: $code-text;
}}

.md-editor {{
    border: solid $md-edit-border;
    background: $md-edit-bg;
    color: $md-edit-text;
}}

.md-render {{
    border: double $md-border;
    background: $bg;
    color: $md-text;
}}

.cell-output {{
    color: $output-text;
    padding: 0 0 0 2;
    border: none;
}}

.cell-error {{
    color: $error;
    padding: 0 0 0 2;
    border: none;
}}

.cell {{
    margin: 0 0 1 0;
}}

#app-status {{
    dock: bottom;
    height: 1;
    background: $header-bg;
    color: $output-text;
}}
"""