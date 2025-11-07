import os
import tempfile

from stageflow.elements import DictElement
from stageflow.loader import load_process


def test_load_process_with_or_logic():
    """Verify process loading works with OR logic locks."""
    process_yaml = """
name: "task_workflow"
description: "Workflow with OR logic"
stages:
  in_progress:
    name: "In Progress"
    gates:
      - name: "complete"
        target_stage: "done"
        locks:
          - type: "OR_LOGIC"
            conditions:
              - locks:
                  - exists: "work_done"
              - locks:
                  - type: "EQUALS"
                    property_path: "cancelled"
                    expected_value: true
                  - exists: "cancellation_reason"
  done:
    name: "Done"
    is_final: true
initial_stage: "in_progress"
final_stage: "done"
"""

    # Create a temporary file with the YAML content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(process_yaml)
        temp_path = f.name

    try:
        process = load_process(temp_path)

        # Test normal completion path
        element1 = DictElement({"work_done": "yes"})
        result1 = process.evaluate(element1, "in_progress")
        assert result1["regression"] is False

        # Test cancellation path
        element2 = DictElement({"cancelled": True, "cancellation_reason": "Duplicate"})
        result2 = process.evaluate(element2, "in_progress")
        assert result2["regression"] is False
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)
