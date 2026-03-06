from backend.graph.pipeline import build_graph


def run():

    graph = build_graph()

    state = {
        "commits": [],
        "dump_text": "",
        "context_summary": "",
        "technical_summary": "",
        "persona": "",
        "x_post": "",
        "linkedin_post": "",
        "thread": "",
        "blog": ""
    }

    result = graph.invoke(state)

    print("\nGenerated Content\n")
    print(result["linkedin_post"])


if __name__ == "__main__":
    run()