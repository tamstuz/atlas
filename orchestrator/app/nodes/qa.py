def run(state: dict) -> dict:
    state["stage"] = "FINAL_REPORT"
    state.setdefault("notes", []).append("QA produced a placeholder verification note.")
    return state
