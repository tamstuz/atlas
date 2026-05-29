def run(state: dict) -> dict:
    state["stage"] = "ANALYST"
    state.setdefault("notes", []).append("Intake captured the user request.")
    return state
