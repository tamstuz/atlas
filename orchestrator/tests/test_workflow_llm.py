from orchestrator.app.schemas.task_packet import TaskPacket
from orchestrator.app.services import workflow_service


def _packet() -> TaskPacket:
    return TaskPacket(
        project_id="project-1",
        task_id="task-1",
        role="analyst",
        phase="analyst",
        objective="Analyze",
        input_summary="Build",
        harness_files_loaded=[],
        allowed_scope=[],
        forbidden_actions=[],
        expected_output="Agent result JSON",
        definition_of_done="Done",
        created_at="2026-05-30T00:00:00Z",
    )


def test_specialist_uses_mocked_llm_response(monkeypatch, tmp_path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "agent-result.schema.json").write_text('{"title": "AgentResult"}', encoding="utf-8")
    monkeypatch.setattr(workflow_service.settings, "harness_dir", tmp_path)
    monkeypatch.setattr(workflow_service.settings, "analyst_model", "analyst-model")

    class Result:
        ok = True
        response = "LLM analyst summary"
        model = "analyst-model"
        provider = "ollama"
        duration_ms = 42
        error = ""

    seen = {}

    def fake_generate(prompt, model):
        seen["prompt"] = prompt
        seen["model"] = model
        return Result()

    monkeypatch.setattr(workflow_service.llm, "generate_sync", fake_generate)

    summary, metadata = workflow_service._run_specialist(
        "analyst",
        {"files": [{"path": "/roles/analyst.md", "content": "Role instructions"}]},
        _packet(),
        {"request": "Create a hello world script"},
    )

    assert summary == "LLM analyst summary"
    assert metadata["llm_used"] is True
    assert metadata["fallback_used"] is False
    assert metadata["model"] == "analyst-model"
    assert "Role instructions" in seen["prompt"]
    assert seen["model"] == "analyst-model"


def test_specialist_falls_back_when_llm_fails(monkeypatch, tmp_path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "agent-result.schema.json").write_text('{"title": "AgentResult"}', encoding="utf-8")
    monkeypatch.setattr(workflow_service.settings, "harness_dir", tmp_path)

    class Result:
        ok = False
        response = ""
        model = "default-model"
        provider = "ollama"
        duration_ms = 7
        error = "connection failed"

    monkeypatch.setattr(workflow_service.llm, "generate_sync", lambda prompt, model: Result())

    summary, metadata = workflow_service._run_specialist(
        "analyst",
        {"files": [{"path": "/roles/analyst.md", "content": "Role instructions"}]},
        _packet(),
        {"request": "Create a hello world script"},
    )

    assert summary == workflow_service.PLACEHOLDER_SUMMARIES["analyst"]
    assert metadata["llm_used"] is False
    assert metadata["fallback_used"] is True
    assert metadata["error"] == "connection failed"
