from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "ai-research-observatory" / "SKILL.md"


def load_skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, _ = text.split("---", maxsplit=2)
    return yaml.safe_load(frontmatter)


def test_observatory_has_its_own_discoverable_skill() -> None:
    assert SKILL_PATH.exists()

    frontmatter = load_skill_frontmatter(SKILL_PATH)
    assert frontmatter["name"] == "ai-research-observatory"

    description = frontmatter["description"]
    assert description.startswith("Use when")
    assert "AI Research Observatory" in description
    assert "ai-observatory" in description


def test_observatory_description_does_not_claim_generic_continuation() -> None:
    description = load_skill_frontmatter(SKILL_PATH)["description"]

    for ambiguous_trigger in ("继续", "AI 资讯", "AI 前沿资讯"):
        assert ambiguous_trigger not in description

