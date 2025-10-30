"""Simple unit tests for automatic stage extraction from element properties."""

import pytest

from stageflow.element import create_element
from stageflow.schema import load_process


def test_stage_extraction_from_yaml(tmp_path):
    """Test stage extraction loading from YAML file."""
    # Create a simple process YAML
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "status"
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    # Load process
    process = load_process(process_yaml)

    # Verify stage_prop is loaded
    assert process.stage_prop == "status"

    # Test auto-extraction
    element = create_element({"status": "start", "ready": True})
    result = process.evaluate(element)
    assert result["stage"] == "start"

    # Test explicit override
    result = process.evaluate(element, "end")
    assert result["stage"] == "end"


def test_stage_extraction_precedence(tmp_path):
    """Test that explicit override takes precedence over auto-extraction."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "status"
  initial_stage: registration
  final_stage: active

  stages:
    registration:
      name: Registration
      gates:
        to_active:
          target_stage: active
          locks:
            - exists: "verified"

    active:
      name: Active
""")

    process = load_process(process_yaml)
    element = create_element({"status": "active", "verified": True})

    # Without override, should use auto-extracted "active"
    result = process.evaluate(element)
    assert result["stage"] == "active"

    # With override, should use "registration" even though element.status="active"
    result = process.evaluate(element, "registration")
    assert result["stage"] == "registration"


def test_stage_prop_not_found_error(tmp_path):
    """Test error when stage property not found in element."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "status"
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    element = create_element({"ready": True})  # Missing "status" field

    with pytest.raises(ValueError) as exc_info:
        process.evaluate(element)

    assert "Stage property 'status' not found in element" in str(exc_info.value)


def test_invalid_stage_name_error(tmp_path):
    """Test error when extracted stage doesn't exist."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "status"
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    element = create_element({"status": "nonexistent"})

    with pytest.raises(ValueError) as exc_info:
        process.evaluate(element)

    error_msg = str(exc_info.value)
    assert "not a valid stage" in error_msg
    assert "Available stages:" in error_msg


def test_nested_property_path(tmp_path):
    """Test stage extraction with nested property path."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "meta.current_stage"
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_middle:
          target_stage: middle
          locks:
            - exists: "ready"

    middle:
      name: Middle
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    element = create_element({"meta": {"current_stage": "middle"}, "ready": True})

    result = process.evaluate(element)
    assert result["stage"] == "middle"


def test_process_without_stage_prop_uses_initial(tmp_path):
    """Test that process without stage_prop defaults to initial_stage."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    element = create_element(
        {"status": "end", "ready": True}
    )  # status should be ignored

    result = process.evaluate(element)
    assert result["stage"] == "start"  # Should use initial_stage, not element.status


def test_to_dict_includes_stage_prop(tmp_path):
    """Test that Process.to_dict() includes stage_prop."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  stage_prop: "status"
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    process_dict = process.to_dict()

    assert "stage_prop" in process_dict
    assert process_dict["stage_prop"] == "status"


def test_to_dict_omits_stage_prop_when_not_configured(tmp_path):
    """Test that Process.to_dict() omits stage_prop when not configured."""
    process_yaml = tmp_path / "process.yaml"
    process_yaml.write_text("""
process:
  name: test_process
  initial_stage: start
  final_stage: end

  stages:
    start:
      name: Start
      gates:
        to_end:
          target_stage: end
          locks:
            - exists: "ready"

    end:
      name: End
""")

    process = load_process(process_yaml)
    process_dict = process.to_dict()

    assert "stage_prop" not in process_dict
