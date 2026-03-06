def build_context(state):

    commits = "\n".join(state["commits"])

    dump = state["dump_text"]

    context = f"""
Project: SaleTech

Developer Activity Today:

Commits:
{commits}

Developer Notes:
{dump}

Extract the main engineering work, improvements, metrics,
and discoveries from this data.
"""

    state["context_summary"] = context

    return state