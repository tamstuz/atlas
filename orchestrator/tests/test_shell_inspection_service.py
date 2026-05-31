from orchestrator.app.services.shell_inspection_service import inspect_command


def test_shell_inspection_rejects_non_allowlisted_commands():
    result = inspect_command(["rm", "-rf", "/tmp/example"], commands_enabled=True)

    assert result["status"] == "rejected"


def test_shell_inspection_does_not_run_by_default():
    result = inspect_command(["pwd"], commands_enabled=False)

    assert result["status"] == "skipped"
    assert "stdout" not in result
