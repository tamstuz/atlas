def run(state: dict) -> dict:
    state["stage"] = "QA"
    state.setdefault("notes", []).append("Developer produced a placeholder work artifact.")
    return state
