from ..services.harness_loader import load_role_bundle


def run(state: dict) -> dict:
    bundle = load_role_bundle("runtime_inspector")
    state.setdefault("notes", []).append("Runtime inspector generated a discover-before-modify inspection plan.")
    state["runtime_inspection_plan"] = {
        "harness_files_loaded": [item["path"] for item in bundle["files"]],
        "steps": [
            "Identify exact runtime paths before proposing changes.",
            "Trace cron, service, or process ownership from registered source files.",
            "Report source files and commands before any modification.",
        ],
        "live_modification_allowed": False,
    }
    return state
