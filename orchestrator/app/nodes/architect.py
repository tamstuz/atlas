def run(state: dict) -> dict:
    state["stage"] = "DEVELOPER"
    state.setdefault("notes", []).append("Architect produced a placeholder implementation outline.")
    return state
