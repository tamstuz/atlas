def run(state: dict) -> dict:
    state["stage"] = "COMPLETE"
    state.setdefault("notes", []).append("Final report placeholder completed the workflow.")
    return state
