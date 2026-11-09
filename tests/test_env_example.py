from pathlib import Path

from app.config import Settings


def test_env_example_lists_every_setting():
    lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
    keys = {line.split("=", 1)[0].lower() for line in lines if "=" in line and line[0] != "#"}
    assert keys == set(Settings.model_fields)
