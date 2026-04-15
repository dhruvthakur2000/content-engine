# ============================================================
# backend/ingestion/dump_parser.py (PRODUCTION VERSION)
# ============================================================

import re
from pathlib import Path
from typing import Optional

from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)


class DumpParserService:
    """
    Service responsible for reading and cleaning developer note dumps.

    Responsibilities:
    - Read notes from file OR API input
    - Normalize and clean text
    - Enforce size limits (LLM-safe)
    - Provide consistent structured logging
    """

    MAX_CHARS = 10_000

    def __init__(self, default_dump_path: str = "inputs/today_dump.txt"):
        self.default_dump_path = default_dump_path

    # =========================================================
    # FILE READING
    # =========================================================

    def read_dump_file(self, file_path: Optional[str] = None) -> str:
        """
        Reads developer notes from disk safely.

        Raises:
            FileNotFoundError
            ValueError (empty or invalid file)
        """

        path = Path(file_path or self.default_dump_path)

        if not path.exists():
            logger.error("dump_file_not_found", path=str(path))
            raise FileNotFoundError(
                f"Notes file not found: {path}\n"
                f"Create it at inputs/today_dump.txt"
            )

        if not path.is_file():
            logger.error("dump_path_not_file", path=str(path))
            raise ValueError(f"Path is not a file: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("dump_file_read_error", path=str(path), error=str(e))
            raise

        if not content.strip():
            logger.warning("dump_file_empty", path=str(path))
            raise ValueError(
                f"Notes file is empty: {path}\n"
                f"Add your daily notes before running the pipeline."
            )

        logger.info(
            "dump_file_read",
            path=str(path),
            chars=len(content),
            lines=content.count("\n"),
        )

        return content

    # =========================================================
    # CLEANING LOGIC
    # =========================================================

    def clean_notes(self, raw_text: str) -> str:
        """
        Cleans and normalizes raw developer notes text.

        Steps:
        - Normalize line endings
        - Remove excessive newlines
        - Remove control characters
        - Trim length (LLM-safe)
        """

        if not raw_text:
            return ""

        text = raw_text.strip()

        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove non-printable characters
        text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", "", text)

        # Trim to max length (LLM-safe)
        if len(text) > self.MAX_CHARS:
            logger.warning(
                "notes_truncated",
                original_chars=len(text),
                truncated_to=self.MAX_CHARS,
            )
            text = (
                text[: self.MAX_CHARS]
                + "\n\n[...notes truncated for length...]"
            )

        return text

    # =========================================================
    # STRING INPUT PARSER (API ENTRY)
    # =========================================================

    def parse_notes_from_string(self, raw_notes: str) -> str:
        """
        Parses notes coming directly from API input.

        This is your most-used path (POST /generate).
        """

        if not raw_notes or not raw_notes.strip():
            logger.error("notes_input_empty")
            raise ValueError("Notes cannot be empty.")

        cleaned = self.clean_notes(raw_notes)

        if len(cleaned) < 10:
            logger.warning("notes_too_short", chars=len(cleaned))

        logger.info(
            "notes_parsed_from_string",
            input_chars=len(raw_notes),
            cleaned_chars=len(cleaned),
        )

        return cleaned

    # =========================================================
    # FILE → CLEAN PIPELINE (HIGH LEVEL)
    # =========================================================

    def load_and_parse_dump(self, file_path: Optional[str] = None) -> str:
        """
        Reads and cleans notes in one step.

        Used for:
        - generate-from-file endpoint
        - CLI workflows
        """

        raw = self.read_dump_file(file_path)
        cleaned = self.clean_notes(raw)

        logger.info(
            "dump_loaded_and_cleaned",
            chars=len(cleaned),
        )

        return cleaned