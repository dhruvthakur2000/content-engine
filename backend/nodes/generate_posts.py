from backend.llm.model import get_llm


def generate_posts(state):

    llm = get_llm()

    prompt = f"""
{state['persona']}

Based on the following engineering activity:

{state['technical_summary']}

Generate:

1. X (Twitter) post
2. LinkedIn post
3. Thread idea
4. Blog outline

Format clearly.
"""

    response = llm.invoke(prompt)

    state["linkedin_post"] = response.content

    return state