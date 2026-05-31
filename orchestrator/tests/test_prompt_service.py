from orchestrator.app.schemas.task_packet import TaskPacket
from orchestrator.app.services.prompt_service import assemble_prompt


def test_prompt_assembly_includes_required_inputs():
    packet = TaskPacket(
        project_id="project-1",
        task_id="task-1",
        role="analyst",
        phase="analyst",
        objective="Analyze the request",
        input_summary="Build a demo",
        harness_files_loaded=["/srv/ai-lab/harness/prod/roles/analyst.md"],
        allowed_scope=["Write project handoff artifacts"],
        forbidden_actions=["Modify harness/prod"],
        expected_output="Agent result JSON",
        definition_of_done="Result written",
        created_at="2026-05-30T00:00:00Z",
    )

    prompt = assemble_prompt(
        "analyst",
        [{"path": "/srv/ai-lab/harness/prod/roles/analyst.md", "content": "Analyst role instructions"}],
        packet,
        "Create a hello world Python script",
        '{"title": "AgentResult"}',
    )

    assert "Analyst role instructions" in prompt
    assert "Create a hello world Python script" in prompt
    assert "Modify harness/prod" in prompt
    assert '"title": "AgentResult"' in prompt
    assert '"role": "analyst"' in prompt
