from typing import TypedDict

from langgraph.graph import END, StateGraph

from .nodes import analyst, architect, developer, final_report, intake, qa


class WorkflowState(TypedDict, total=False):
    project_id: str
    request: str
    stage: str
    notes: list[str]


def build_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("intake", intake.run)
    graph.add_node("analyst", analyst.run)
    graph.add_node("architect", architect.run)
    graph.add_node("developer", developer.run)
    graph.add_node("qa", qa.run)
    graph.add_node("final_report", final_report.run)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "analyst")
    graph.add_edge("analyst", "architect")
    graph.add_edge("architect", "developer")
    graph.add_edge("developer", "qa")
    graph.add_edge("qa", "final_report")
    graph.add_edge("final_report", END)
    return graph.compile()


def run_workflow(state: WorkflowState) -> WorkflowState:
    return build_graph().invoke(state)
