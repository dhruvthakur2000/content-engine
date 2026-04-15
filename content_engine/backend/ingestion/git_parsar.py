# ============================================================
# backend/ingestion/git_ingestion.py
#
# PRODUCTION VERSION — LOW LATENCY + STRUCTURED OUTPUT
# ============================================================

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class GitCommit:
    hash: str
    message: str
    files_changed: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0


@dataclass
class GitIngestionResult:
    repo_name: str
    branch: str
    commits: List[GitCommit]
    total_additions: int
    total_deletions: int
    files_touched: List[str]
    today_summary: str
    error: Optional[str] = None

    # --------------------------------------------------------
    # Convert structured data → LLM-friendly string
    # --------------------------------------------------------
    def to_pipeline_string(self) -> str:
        if self.error:
            return f"[GIT LOG UNAVAILABLE]\nReason: {self.error}"

        lines = [
            f"Repository: {self.repo_name}",
            f"Branch: {self.branch}",
            f"Total changes: +{self.total_additions} -{self.total_deletions}",
            "",
            "=== COMMITS ===",
        ]

        for c in self.commits:
            lines.append(f"[{c.hash[:7]}] {c.message}")
            lines.append(f"Files: {', '.join(c.files_changed)}")
            lines.append(f"Changes: +{c.additions} -{c.deletions}")
            lines.append("")

        lines.append("=== TODAY SUMMARY ===")
        lines.append(self.today_summary)

        return "\n".join(lines)


# ============================================================
# CORE INGESTION FUNCTION
# ============================================================

def auto_ingest_git(repo_path: str = ".", max_commits: int = 5) -> GitIngestionResult:
    """
    Extract today's git activity (commits + file changes + stats)

    This function NEVER crashes — always returns structured result.
    """

    try:
        repo_name = _run_git_command(["rev-parse", "--show-toplevel"], repo_path).split("/")[-1]
        branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)

        raw_log = _run_git_command(
            ["log", "--since=midnight", "--pretty=format:%H||%s", f"-{max_commits}"],
            repo_path,
        )

        if not raw_log.strip():
            return _empty_result(repo_name, branch, reason="No commits today")

        commits = []
        total_add = 0
        total_del = 0
        all_files = set()

        for line in raw_log.split("\n"):
            if "||" not in line:
                continue

            commit_hash, message = line.split("||", 1)

            stats = _get_commit_stats(commit_hash, repo_path)

            commits.append(
                GitCommit(
                    hash=commit_hash,
                    message=message,
                    files_changed=stats["files"],
                    additions=stats["additions"],
                    deletions=stats["deletions"],
                )
            )

            total_add += stats["additions"]
            total_del += stats["deletions"]
            all_files.update(stats["files"])

        summary = _build_summary(commits)

        return GitIngestionResult(
            repo_name=repo_name,
            branch=branch,
            commits=commits,
            total_additions=total_add,
            total_deletions=total_del,
            files_touched=list(all_files),
            today_summary=summary,
        )

    except Exception as e:
        logger.error("git_ingestion_failed", error=str(e))

        return GitIngestionResult(
            repo_name="unknown",
            branch="unknown",
            commits=[],
            total_additions=0,
            total_deletions=0,
            files_touched=[],
            today_summary="Git ingestion failed.",
            error=str(e),
        )


# ============================================================
# HELPERS
# ============================================================

def _run_git_command(cmd: List[str], repo_path: str) -> str:
    """Run git command safely"""
    result = subprocess.run(
        ["git"] + cmd,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=5,   # prevent hanging
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def _get_commit_stats(commit_hash: str, repo_path: str) -> dict:
    """Extract file changes + line stats for a commit"""
    try:
        output = _run_git_command(
            ["show", "--stat", "--oneline", commit_hash],
            repo_path,
        )

        files = []
        additions = 0
        deletions = 0

        for line in output.split("\n"):
            if "|" in line:
                file_name = line.split("|")[0].strip()
                files.append(file_name)

            if "+" in line or "-" in line:
                additions += line.count("+")
                deletions += line.count("-")

        return {
            "files": files[:5],  # limit for prompt size
            "additions": additions,
            "deletions": deletions,
        }

    except Exception:
        return {"files": [], "additions": 0, "deletions": 0}


def _build_summary(commits: List[GitCommit]) -> str:
    """Generate simple deterministic summary (no LLM)"""

    if not commits:
        return "No commits detected."

    return (
        f"{len(commits)} commits made today. "
        f"Worked across {len(set(f for c in commits for f in c.files_changed))} files."
    )


def _empty_result(repo: str, branch: str, reason: str) -> GitIngestionResult:
    """Return safe empty result"""
    return GitIngestionResult(
        repo_name=repo,
        branch=branch,
        commits=[],
        total_additions=0,
        total_deletions=0,
        files_touched=[],
        today_summary=reason,
        error=reason,
    )