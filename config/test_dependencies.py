"""Bağımlılıklar hem requirements.txt hem pyproject.toml'da tutulur; ikisi ayrışmamalı.

Vercel bağımlılıkları requirements.txt veya pyproject.toml'dan kurabilir. İkisi farklı olursa
canlıda sessizce eksik paketle çalışılır.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def requirements(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return sorted(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def test_pyproject_dependencies_match_requirements_txt():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert sorted(pyproject["project"]["dependencies"]) == requirements(ROOT / "requirements.txt")


def test_dev_tools_are_not_production_dependencies():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = " ".join(pyproject["project"]["dependencies"]).lower()

    for dev_tool in ("pytest", "ruff"):
        assert dev_tool not in declared
