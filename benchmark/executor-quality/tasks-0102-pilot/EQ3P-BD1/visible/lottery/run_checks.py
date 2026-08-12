import pathlib


scope = {}
source = pathlib.Path(__file__).parents[1] / "assignments" / "plot_assigner.py"
exec(source.read_text(encoding="utf-8"), scope)
print(scope["open_season"]()["released"])
