import pathlib


scope = {}
path = pathlib.Path(__file__).parents[1] / "editor" / "combo_editor.py"
exec(path.read_text(encoding="utf-8"), scope)

if __name__ == "__main__":
    shift = scope["open_shift"]()
    scope["reserve_combo"](shift)
    scope["expire_component"](shift, "fizz")
    assert shift["refunds"] == 1
    assert shift["stock"]["corn"] == 2
    assert not scope["combo_available"](shift)
    assert shift["spoilage"] == 1
