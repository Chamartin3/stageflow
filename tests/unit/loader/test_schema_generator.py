"""Unit tests for schema generation functionality."""

import json
from typing import cast

import pytest

from stageflow import Process
from stageflow.elements.schema import RequiredFieldAnalyzer, SchemaGenerator
from stageflow.models import ProcessDefinition


@pytest.fixture
def simple_process_with_exists():
    """Simple 2-stage process with EXISTS locks."""
    config = cast(
        ProcessDefinition,
        {
            "name": "simple_test",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "expected_properties": {
                        "email": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [{"exists": "email"}],
                        }
                    ],
                },
                "end": {"is_final": True},
            },
        },
    )
    return Process(config)


@pytest.fixture
def multi_stage_process():
    """Multi-stage process for cumulative testing."""
    config = cast(
        ProcessDefinition,
        {
            "name": "multi_stage_test",
            "initial_stage": "stage1",
            "final_stage": "stage3",
            "stages": {
                "stage1": {
                    "expected_properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "gates": [
                        {
                            "name": "to_stage2",
                            "target_stage": "stage2",
                            "locks": [{"exists": "email"}],
                        }
                    ],
                },
                "stage2": {
                    "expected_properties": {
                        "age": {"type": "integer"},
                        "verified": {"type": "boolean"},
                    },
                    "gates": [
                        {
                            "name": "to_stage3",
                            "target_stage": "stage3",
                            "locks": [{"exists": "verified"}],
                        }
                    ],
                },
                "stage3": {
                    "expected_properties": {"profile_complete": {"type": "boolean"}},
                    "is_final": True,
                },
            },
        },
    )
    return Process(config)


@pytest.fixture
def process_with_conditional_locks():
    """Process with CONDITIONAL locks containing EXISTS."""
    config = cast(
        ProcessDefinition,
        {
            "name": "conditional_test",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "expected_properties": {
                        "type": {"type": "string"},
                        "email": {"type": "string"},
                        "company": {"type": "string"},
                    },
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [
                                {
                                    "type": "CONDITIONAL",
                                    "if": [{"exists": "email"}],
                                    "then": [{"exists": "company"}],
                                }
                            ],
                        }
                    ],
                },
                "end": {"is_final": True},
            },
        },
    )
    return Process(config)


@pytest.fixture
def process_with_or_logic():
    """Process with OR_LOGIC locks containing EXISTS."""
    config = cast(
        ProcessDefinition,
        {
            "name": "or_logic_test",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "expected_properties": {
                        "approved": {"type": "boolean"},
                        "rejected": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "gates": [
                        {
                            "name": "to_end",
                            "target_stage": "end",
                            "locks": [
                                {
                                    "type": "OR_LOGIC",
                                    "conditions": [
                                        {"locks": [{"exists": "approved"}]},
                                        {
                                            "locks": [
                                                {"exists": "rejected"},
                                                {"exists": "reason"},
                                            ]
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "end": {"is_final": True},
            },
        },
    )
    return Process(config)


class TestRequiredFieldAnalyzer:
    """Test RequiredFieldAnalyzer functionality."""

    def test_exists_lock_detection_simple(self, simple_process_with_exists):
        """Test EXISTS lock detection in simple gates."""
        analyzer = RequiredFieldAnalyzer()
        stage = simple_process_with_exists.stages[0]  # start stage

        required = analyzer.analyze_stage(stage)

        assert "email" in required
        assert "age" not in required

    def test_exists_lock_detection_conditional(self, process_with_conditional_locks):
        """Test EXISTS lock detection in CONDITIONAL locks."""
        analyzer = RequiredFieldAnalyzer()
        stage = process_with_conditional_locks.stages[0]  # start stage

        required = analyzer.analyze_stage(stage)

        # Should find EXISTS locks in both 'if' and 'then' conditions
        assert "email" in required
        assert "company" in required
        assert "type" not in required

    def test_exists_lock_detection_or_logic(self, process_with_or_logic):
        """Test EXISTS lock detection in OR_LOGIC locks."""
        analyzer = RequiredFieldAnalyzer()
        stage = process_with_or_logic.stages[0]  # start stage

        required = analyzer.analyze_stage(stage)

        # Should find EXISTS locks in all OR conditions
        assert "approved" in required
        assert "rejected" in required
        assert "reason" in required

    def test_no_exists_locks(self):
        """Test when no EXISTS locks present (all optional)."""
        config = cast(
            ProcessDefinition,
            {
                "name": "no_exists_test",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "expected_properties": {
                            "email": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                        "gates": [
                            {
                                "name": "to_end",
                                "target_stage": "end",
                                "locks": [
                                    {
                                        "type": "EQUALS",
                                        "property_path": "age",
                                        "expected_value": 18,
                                    }
                                ],
                            }
                        ],
                    },
                    "end": {"is_final": True},
                },
            },
        )
        process = Process(config)
        analyzer = RequiredFieldAnalyzer()
        stage = process.stages[0]  # start stage

        required = analyzer.analyze_stage(stage)

        # No EXISTS locks, so no required fields
        assert len(required) == 0

    def test_clean_property_path_with_length(self):
        """Test cleaning property paths with length() wrapper."""
        analyzer = RequiredFieldAnalyzer()

        # Test with length wrapper
        assert analyzer._clean_property_path("length(items)") == "items"

        # Test without wrapper
        assert analyzer._clean_property_path("email") == "email"

        # Test empty
        assert analyzer._clean_property_path("") == ""


class TestSchemaGenerator:
    """Test SchemaGenerator functionality."""

    def test_stage_specific_schema_uses_get_schema(self, multi_stage_process):
        """Test that stage-specific generation uses Stage.get_schema()."""
        generator = SchemaGenerator(multi_stage_process)

        # Get stage directly and its schema
        stage = generator._get_stage("stage2")
        expected_schema = stage.get_schema()

        # Generate schema
        result = generator.generate_stage_schema("stage2")

        # Verify properties match Stage.get_schema()
        assert "properties" in result
        for prop_name in expected_schema:
            assert prop_name in result["properties"]

        # Should only have stage2 properties
        assert "age" in result["properties"]
        assert "verified" in result["properties"]
        assert "email" not in result["properties"]  # from stage1
        assert "name" not in result["properties"]  # from stage1

    def test_cumulative_schema_merges_stages(self, multi_stage_process):
        """Test that cumulative schema merges from multiple stages."""
        generator = SchemaGenerator(multi_stage_process)

        schema = generator.generate_cumulative_schema("stage3")

        # Should include properties from all stages in path (stage1 -> stage2 -> stage3)
        assert "properties" in schema
        assert "email" in schema["properties"]  # from stage1
        assert "name" in schema["properties"]  # from stage1
        assert "age" in schema["properties"]  # from stage2
        assert "verified" in schema["properties"]  # from stage2
        assert "profile_complete" in schema["properties"]  # from stage3

    def test_empty_schema_handling(self):
        """Test handling of stages with no expected_properties."""
        config = cast(
            ProcessDefinition,
            {
                "name": "empty_schema_test",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "gates": [
                            {
                                "name": "to_end",
                                "target_stage": "end",
                                "locks": [{"exists": "complete"}],
                            }
                        ]
                    },
                    "end": {"is_final": True},
                },
            },
        )
        process = Process(config)
        generator = SchemaGenerator(process)

        schema = generator.generate_stage_schema("start")

        # Should still be valid JSON Schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert "complete" in schema["required"]

    def test_schema_merging_override(self):
        """Test that later stages override earlier stages."""
        config = cast(
            ProcessDefinition,
            {
                "name": "override_test",
                "initial_stage": "stage1",
                "final_stage": "stage2",
                "stages": {
                    "stage1": {
                        "expected_properties": {
                            "email": {"type": "string", "default": "user@example.com"}
                        },
                        "gates": [
                            {
                                "name": "to_stage2",
                                "target_stage": "stage2",
                                "locks": [{"exists": "email"}],
                            }
                        ],
                    },
                    "stage2": {
                        "expected_properties": {
                            "email": {
                                "type": "string",
                                "default": "admin@example.com",
                            }  # override
                        },
                        "is_final": True,
                    },
                },
            },
        )
        process = Process(config)
        generator = SchemaGenerator(process)

        schema = generator.generate_cumulative_schema("stage2")

        # Should have email property with the later stage's default
        assert "email" in schema["properties"]
        assert schema["properties"]["email"]["default"] == "admin@example.com"

    def test_path_finding_linear(self, multi_stage_process):
        """Test BFS path finding with linear stage progression."""
        generator = SchemaGenerator(multi_stage_process)

        path = generator._get_stage_path("stage3")

        # Should find path: stage1 -> stage2 -> stage3
        assert path == ["stage1", "stage2", "stage3"]

    def test_path_finding_unreachable_stage(self):
        """Test error handling for unreachable stages."""
        config = cast(
            ProcessDefinition,
            {
                "name": "unreachable_test",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": {
                    "start": {
                        "gates": [
                            {
                                "name": "to_middle",
                                "target_stage": "middle",
                                "locks": [{"exists": "ready"}],
                            }
                        ]
                    },
                    "middle": {
                        "gates": [
                            {
                                "name": "to_end",
                                "target_stage": "end",
                                "locks": [{"exists": "approved"}],
                            }
                        ]
                    },
                    "unreachable": {},  # No path from start
                    "end": {"is_final": True},
                },
            },
        )
        process = Process(config)
        generator = SchemaGenerator(process)

        path = generator._get_stage_path("unreachable")

        # Should return empty list for unreachable stage
        assert path == []

    def test_path_finding_initial_as_target(self, multi_stage_process):
        """Test when initial stage is also target."""
        generator = SchemaGenerator(multi_stage_process)

        path = generator._get_stage_path("stage1")

        # Should return just the initial stage
        assert path == ["stage1"]

    def test_yaml_output_format(self, simple_process_with_exists):
        """Test YAML output formatting."""
        generator = SchemaGenerator(simple_process_with_exists)

        schema = generator.generate_stage_schema("start")
        yaml_output = generator.to_yaml(schema)

        # Should be valid YAML string
        assert isinstance(yaml_output, str)
        assert "$schema" in yaml_output
        assert "type: object" in yaml_output

    def test_json_output_format(self, simple_process_with_exists):
        """Test JSON output formatting."""
        generator = SchemaGenerator(simple_process_with_exists)

        schema = generator.generate_stage_schema("start")
        json_output = generator.to_json(schema)

        # Should be valid JSON string
        assert isinstance(json_output, str)
        parsed = json.loads(json_output)
        assert parsed["type"] == "object"
        assert "$schema" in parsed

    def test_type_mapping(self):
        """Test StageFlow to JSON Schema type mapping."""
        generator = SchemaGenerator(None)  # Don't need process for this test

        # Test various type mappings
        assert generator._map_type("string") == "string"
        assert generator._map_type("str") == "string"
        assert generator._map_type("integer") == "integer"
        assert generator._map_type("int") == "integer"
        assert generator._map_type("boolean") == "boolean"
        assert generator._map_type("bool") == "boolean"
        assert generator._map_type("number") == "number"
        assert generator._map_type("float") == "number"
        assert generator._map_type("array") == "array"
        assert generator._map_type("list") == "array"
        assert generator._map_type("object") == "object"
        assert generator._map_type("dict") == "object"

        # Test unknown type defaults to string
        assert generator._map_type("unknown") == "string"

    def test_invalid_stage_error(self, simple_process_with_exists):
        """Test error handling for non-existent stages."""
        generator = SchemaGenerator(simple_process_with_exists)

        with pytest.raises(ValueError, match="Stage 'nonexistent' not found"):
            generator.generate_stage_schema("nonexistent")

        with pytest.raises(ValueError, match="Stage 'nonexistent' not found"):
            generator.generate_cumulative_schema("nonexistent")
