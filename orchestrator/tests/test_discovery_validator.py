from orchestrator.app.services.discovery_validator import validate_discovery


def test_discovery_validator_blocks_incomplete_findings():
    result = validate_discovery({"current_observed_behavior": "request received"})

    assert result["safe_to_modify"] is False
    assert "Exact command" in result["missing_requirements"]
    assert result["confidence"] == "low"
