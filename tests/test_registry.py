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


def test_registry_enables_official_html_sources_with_verified_contracts():
    registry = load_registry(ROOT / "config/targets.yaml", ROOT / "config/themes.yaml")
    sources = {
        source.id: source
        for target in registry.targets
        for source in target.sources
        if source.id in {"anthropic_news_html", "meta_ai_blog_html"}
    }
    assert set(sources) == {"anthropic_news_html", "meta_ai_blog_html"}
    for source in sources.values():
        assert source.enabled is True
        assert source.config["max_items"] == 20
        assert source.config["date_selector"]
        assert source.config["date_formats"]
        assert source.config["item_selector"]
        assert source.config["title_selector"]
        assert source.config["link_selector"]
    assert sources["anthropic_news_html"].config["date_formats"] == ["%b %d, %Y", "%B %d, %Y"]
    assert sources["meta_ai_blog_html"].config["date_formats"] == ["%B %d, %Y", "%b %d, %Y"]
