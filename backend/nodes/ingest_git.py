from git import Repo

def ingest_git(state):

    repo = Repo(".")

    commits = repo.iter_commits(max_count=10)

    commit_messages = []

    for commit in commits:
        commit_messages.append(commit.message.strip())

    state["commits"] = commit_messages

    return state