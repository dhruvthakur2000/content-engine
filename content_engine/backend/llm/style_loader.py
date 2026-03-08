# ============================================================
# backend/llm/style_loader.py
#
# PURPOSE: Loads creator style profiles from markdown files
# and injects them into LLM prompts as writing guidance.
# ============================================================

from pathlib import Path
from functools import lru_cache
from typing import List

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# Directory where style profiles live
STYLE_DIR = (Path(__file__).parent.parent.parent / "creator_styles").resolve()


# Built-in fallback style
_FALLBACK_STYLE = """
Style: Authentic developer voice.

Hook: Lead with the most surprising or specific fact.
Rhythm: Short sentences. One idea per line.
Tone: Direct. Technical. Human. Never corporate.
Structure: Hook → context → insight → technical proof → lesson.
Rule: Specific beats vague. Numbers beat adjectives. Show don't tell.
Anti-patterns to avoid: "excited to share", "learnings", "game-changer".
""".strip()


@lru_cache(maxsize=32)
def load_style(style_name: str) -> str:
    """
    Loads a creator style profile from creator_styles/.

    Cached to avoid repeated disk reads.

    Args:
        style_name: style filename without extension.

    Returns:
        Markdown content of the style guide.
    """

    style_name = (style_name or "").strip().lower()

    if not style_name or style_name == "default":
        logger.info("style_loaded", style="fallback")
        return _FALLBACK_STYLE

    style_path = STYLE_DIR / f"{style_name}.md"

    if not style_path.exists():
        logger.warning(
            "style_file_not_found",
            requested=style_name,
            path=str(style_path),
            fallback="using default style",
        )
        return _FALLBACK_STYLE

    try:
        content = style_path.read_text(encoding="utf-8").strip()

        logger.info(
            "style_loaded",
            style=style_name,
            chars=len(content),
        )

        return content

    except Exception as e:

        logger.error(
            "style_load_error",
            style=style_name,
            error=str(e),
        )

        return _FALLBACK_STYLE


def list_available_styles() -> List[str]:
    """
    Returns list of available style profiles.

    Used by API/UI to populate style selector.
    """

    if not STYLE_DIR.exists():
        logger.warning("style_dir_not_found", path=str(STYLE_DIR))
        return []

    styles = sorted([f.stem for f in STYLE_DIR.glob("*.md")])

    logger.info(
        "styles_listed",
        count=len(styles),
        styles=styles,
    )

    return styles