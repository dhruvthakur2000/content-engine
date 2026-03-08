import re
from pathlib import Path
from typing import Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DumpParserService:
    """
    Service responsible for reading and cleaning developer note dumps.

    This class wraps the previous utility functions into a single
    cohesive service while preserving the exact logic.
    """

    MAX_CHARS = 10_000

    def __init__(self, default_dump_path: str = "inputs/today_dump.txt"):
        """
        Initialize parser with a default dump file location.

        Args:
            default_dump_path: default location of notes file
        """
        self.default_dump_path = default_dump_path

    # ---------------------------------------------------------
    # FILE READING
    # ---------------------------------------------------------

    def read_dump_file(self, file_path: Optional[str] = None) -> str:
        """
        Reads a developer notes file from disk and returns raw text.
        """

        path = Path(file_path or self.default_dump_path)

        if not path.exists():
            logger.error("dump_file_not_found", path=str(path))
            raise FileNotFoundError(
                f"Notes file not found: {path}\n"
                f"Create it at inputs/today_dump.txt"
            )

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

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

    # ---------------------------------------------------------
    # CLEANING LOGIC
    # ---------------------------------------------------------

    def clean_notes(self, raw_text: str) -> str:
        """
        Cleans and normalizes raw developer notes text.
        """

        text = raw_text.strip()

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        text = re.sub(r"\n{3,}", "\n\n", text)

        text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", "", text)

        if len(text) > self.MAX_CHARS:
            logger.warning(
                "notes_truncated",
                original_chars=len(text),
                truncated_to=self.MAX_CHARS,
            )
            text = text[: self.MAX_CHARS] + "\n\n[...notes truncated for length...]"

        return text

    # ---------------------------------------------------------
    # STRING INPUT PARSER
    # ---------------------------------------------------------

    def parse_notes_from_string(self, raw_notes: str) -> str:
        """
        Parses notes coming directly from API input.
        """

        if not raw_notes or not raw_notes.strip():
            raise ValueError("Notes cannot be empty.")

        cleaned = self.clean_notes(raw_notes)

        logger.info(
            "notes_parsed_from_string",
            chars=len(cleaned),
        )

        return cleaned

    # ---------------------------------------------------------
    # HIGH LEVEL PIPELINE ENTRYPOINT
    # ---------------------------------------------------------

    def load_and_parse_dump(self, file_path: Optional[str] = None) -> str:
        """
        Reads and cleans notes in one step.
        """

        raw = self.read_dump_file(file_path)
        cleaned = self.clean_notes(raw)

        return cleaned