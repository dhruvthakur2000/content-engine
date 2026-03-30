import subprocess


def get_git_log_since(since="yesterday", until="now"):
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={since}",
                f"--until={until}",
                '--pretty=format:%h | %ad | %s',
                '--date=iso'
            ],
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    except Exception as e:
        return f"[GIT LOG UNAVAILABLE] {str(e)}"