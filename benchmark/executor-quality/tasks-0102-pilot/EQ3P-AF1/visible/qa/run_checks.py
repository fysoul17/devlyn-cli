import pathlib


scope = {}
path = pathlib.Path(__file__).parents[1] / "editor" / "combo_editor.py"
exec(path.read_text(encoding="utf-8"), scope)
print(scope["combo_available"](scope["open_shift"]()))
