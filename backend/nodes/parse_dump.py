def parse_dump(state):

    with open("inputs/today_dump.txt", "r") as f:
        text = f.read()

    state["dump_text"] = text

    return state