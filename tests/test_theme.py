import json

from lynx_notebook.tui.theme import CSS, editor_theme, load_theme


def test_default_theme_has_both_modes():
    theme = load_theme(user_path=None)
    assert {"dark", "light"} <= set(theme.data["themes"])
    for mode in ("dark", "light"):
        t = theme.with_mode(mode)
        editor_theme(t)
        assert all(f"lx-{k}" for k in t.css_variables())


def test_css_only_uses_defined_variables():
    import re

    theme = load_theme(user_path=None)
    defined = set(theme.css_variables())
    used = set(re.findall(r"\$(lx-[\w-]+)", CSS))
    assert used <= defined


def test_user_file_overrides_and_merges(tmp_path):
    f = tmp_path / "theme.json"
    f.write_text(json.dumps({"themes": {"dark": {"accent": "#ff0000"}}, "spacing": {"cell_gap": 2}}))
    theme = load_theme(user_path=f)
    assert theme.colors["accent"] == "#ff0000"
    assert theme.colors["bg"]  # untouched keys remain
    assert theme.spacing["cell_gap"] == 2


def test_broken_user_file_falls_back(tmp_path):
    f = tmp_path / "theme.json"
    f.write_text("{ nope")
    assert load_theme(user_path=f).colors["accent"] == "#0A84FF"
