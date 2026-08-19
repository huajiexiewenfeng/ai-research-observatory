from pathlib import Path

import pytest

from ai_observatory.registry import RegistryError, load_registry


ROOT = Path(__file__).parents[1]


def test_registry_contains_approved_target_pool():
    registry = load_registry(ROOT / "config/targets.yaml", ROOT / "config/themes.yaml")
    assert len(registry.by_kind("company")) == 17
    assert len(registry.by_kind("project")) == 28
    assert len(registry.by_kind_and_tier("company", "core")) == 6
    assert len(registry.by_kind_and_tier("project", "core")) == 8


def test_registry_rejects_unknown_theme(tmp_path):
    targets = tmp_path / "targets.yaml"
    themes = tmp_path / "themes.yaml"
    targets.write_text(
        "targets:\n  - id: bad\n    name: Bad\n    kind: project\n    tier: core\n"
        "    themes: [missing]\n    sources: []\n",
        encoding="utf-8",
    )
    themes.write_text("themes: []\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown theme: missing"):
        load_registry(targets, themes)
