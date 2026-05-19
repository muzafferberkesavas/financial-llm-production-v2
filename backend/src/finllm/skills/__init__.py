"""Skill markdown files — loaded at runtime by ClaudeClient for system prompts.

Skills are Anthropic-format markdown with YAML frontmatter.
ClaudeClient reads SKILL.md content and uses it as system prompt.
"""
from pathlib import Path

SKILLS_DIR = Path(__file__).parent


def load_skill(name: str) -> str:
    """Load skill content (full markdown) by name."""
    skill_path = SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    return skill_path.read_text()


__all__ = ["SKILLS_DIR", "load_skill"]
