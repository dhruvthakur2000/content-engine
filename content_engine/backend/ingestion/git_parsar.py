from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)


class GitLogService:
    """
    Service responsible for reading and parsing Git commit history.
    This class encapsulates Git interactions so the pipeline can easily
    obtain commit summaries for content generation.
    """

    MAX_CHARS = 3000

    def __init__(self, repo_path: str = "."):
        """
        Initialize the service.

        Args:
            repo_path: Path to the git repository.
        """
        self.repo_path = Path(repo_path).resolve()

    def get_git_log(self, days_back: int = 1, max_commits: int = 20) -> str:
        """
        Reads recent git commits and returns formatted text.

        Args:
            days_back: Number of days of history to include.
            max_commits: Maximum commits to return.

        Returns:
            Formatted commit string.
        """

        try:
            import git
        except ImportError:
            logger.warning("GitPython_not_installed")
            return self._fallback_message(
                "GitPython not installed. Run: uv pip install GitPython"
            )

        if not self.repo_path.exists():
            logger.warning("git_repo_path_not_found", path=str(self.repo_path))
            return self._fallback_message(
                f"Path not found: {self.repo_path}"
            )

        try:
            repo = git.Repo(str(self.repo_path), search_parent_directories=True)
        except git.exc.InvalidGitRepositoryError:
            logger.warning("not_a_git_repo", path=str(self.repo_path))
            return self._fallback_message(
                f"Directory is not a git repository: {self.repo_path}\n"
                "Initialize with: git init && git add . && git commit -m 'initial commit'"
            )
        except git.exc.NoSuchPathError:
            return self._fallback_message(f"Git path error: {self.repo_path}")

        cutoff_dt = datetime.now(tz=timezone.utc) - timedelta(days=days_back)

        commits: List[str] = []

        try:
            for commit in repo.iter_commits("HEAD", max_count=max_commits):

                if commit.committed_datetime < cutoff_dt:
                    break

                formatted_time = commit.committed_datetime.strftime("%Y-%m-%d %H:%M")

                commit_line = f"{commit.message.strip()} ({formatted_time})"

                commits.append(commit_line)

        except Exception as e:
            logger.error("git_log_read_error", error=str(e))
            return self._fallback_message(f"Error reading git log: {e}")

        if not commits:
            logger.info(
                "no_commits_found",
                days_back=days_back,
                repo=str(self.repo_path),
            )
            return self._fallback_message(
                f"No commits found in the last {days_back} day(s).\n"
                "Make some commits and try again."
            )

        git_log_text = "\n".join(commits)

        logger.info(
            "git_log_read",
            commit_count=len(commits),
            days_back=days_back,
            repo=str(self.repo_path),
        )

        return git_log_text
    
    def parse_git_log_string(self, raw_git_log: str) -> str:
        """
        Cleans a manually provided git log string.

        Args:
            raw_git_log: Raw git log text.

        Returns:
            Cleaned git log string.
        """

        if not raw_git_log or not raw_git_log.strip():
            return self._fallback_message("No git log provided.")

        cleaned = raw_git_log.strip()

        if len(cleaned) > self.MAX_CHARS:
            cleaned = cleaned[: self.MAX_CHARS] + "\n[...git log truncated...]"
            logger.warning("git_log_truncated")

        return cleaned

    def _fallback_message(self, reason: str) -> str:
        """
        Returns fallback message when git log can't be read.
        """

        return f"[GIT LOG UNAVAILABLE: {reason}]"