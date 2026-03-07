from pathlib import Path        # Modern path handling
from typing import Optional     # Type hint for optional return

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Directory where all creator style .md files live.
# Path(__file__) = this file's path → .parent.parent.parent = project root
STYLE_DIR = Path(__file__).parent.parent.parent / "creator_styles"

# Built-in fallback style — used when no style is selected
# or when the requested style file doesn't exist.
# This is neutral guidance that still prevents generic AI output.
_FALLBACK_STYLE = """
Style: Authentic developer voice.

Hook: Lead with the most surprising or specific fact.
Rhythm: Short sentences. One idea per line.
Tone: Direct. Technical. Human. Never corporate.
Structure: Hook → context → insight → technical proof → lesson.
Rule: Specific beats vague. Numbers beat adjectives. Show don't tell.
Anti-patterns to avoid: "excited to share", "learnings", "game-changer".
"""