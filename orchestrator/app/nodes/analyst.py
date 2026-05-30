def run(state: dict) -> dict:
    state["stage"] = "ARCHITECT"
    state.setdefault("notes", []).append("Analyst produced a placeholder requirements summary.")
    return state
