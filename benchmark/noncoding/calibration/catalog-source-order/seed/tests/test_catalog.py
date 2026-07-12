from src.catalog import command


def test_existing_command_is_available() -> None:
    assert command("export")["timeout_seconds"] == 60
