import pathlib


scope = {}
source = pathlib.Path(__file__).parents[1] / "assignments" / "plot_assigner.py"
exec(source.read_text(encoding="utf-8"), scope)

if __name__ == "__main__":
    season = scope["open_season"]()
    scope["abandon_plot"](season, "north")
    scope["abandon_plot"](season, "north")
    assert season["released"] == 1
    assert "ada" not in season["water"]
    assert season["lottery"] == ["north"]
    assert season["waitlist"] == ["bo", "cy"]
