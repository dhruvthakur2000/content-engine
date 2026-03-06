from backend.llm.model import get_llm


def summarize_context(state):

    llm = get_llm()

    prompt = f"""
Summarize the following developer activity into a clear
technical explanation.

{state['context_summary']}
"""

    response = llm.invoke(prompt)

    state["technical_summary"] = response.content

    return state