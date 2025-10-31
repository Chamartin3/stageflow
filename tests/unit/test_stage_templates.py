"""Unit tests for stage template functionality."""

import pytest

from stageflow.stage import Stage, StageDefinition


class TestTemplateValidation:
    """Test template validation logic."""

    def test_template_valid(self):
        """Test valid template passes validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test template",
                    "parameters": [
                        {
                            "name": "param1",
                            "required": True,
                            "description": "Test param",
                        }
                    ],
                    "frontmatter": {"type": "test"},
                    "sections": [{"id": "section1", "title": "Section 1", "level": 1}],
                }
            ],
        }

        stage = Stage("test_stage", config)
        assert len(stage.templates) == 1
        assert stage.templates[0]["name"] == "test_template"

    def test_template_missing_name(self):
        """Test template without name fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"description": "Test template"}],  # Missing name
        }

        with pytest.raises(ValueError, match="missing required 'name' field"):
            Stage("test_stage", config)

    def test_template_missing_description(self):
        """Test template without description fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"name": "test_template"}],  # Missing description
        }

        with pytest.raises(ValueError, match="missing required 'description' field"):
            Stage("test_stage", config)

    def test_template_duplicate_names(self):
        """Test duplicate template names fail validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {"name": "duplicate", "description": "First"},
                {"name": "duplicate", "description": "Second"},
            ],
        }

        with pytest.raises(ValueError, match="Duplicate template name 'duplicate'"):
            Stage("test_stage", config)

    def test_template_parameter_validation(self):
        """Test parameter validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "parameters": [
                        {"name": "param1"}  # Missing required and description
                    ],
                }
            ],
        }

        with pytest.raises(
            ValueError,
            match="missing required 'required' field|missing required 'description' field",
        ):
            Stage("test_stage", config)

    def test_template_parameter_missing_name(self):
        """Test parameter without name fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "parameters": [
                        {
                            "required": True,
                            "description": "Test param",
                        }  # Missing name
                    ],
                }
            ],
        }

        with pytest.raises(ValueError, match="missing required 'name' field"):
            Stage("test_stage", config)

    def test_template_duplicate_parameter_names(self):
        """Test duplicate parameter names fail validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "parameters": [
                        {"name": "duplicate", "required": True, "description": "First"},
                        {
                            "name": "duplicate",
                            "required": False,
                            "description": "Second",
                        },
                    ],
                }
            ],
        }

        with pytest.raises(ValueError, match="Duplicate parameter name 'duplicate'"):
            Stage("test_stage", config)

    def test_template_section_validation(self):
        """Test section validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [
                        {"id": "section1", "title": "Section 1", "level": 1},
                        {"id": "section2", "title": "Section 2", "level": 2},
                    ],
                }
            ],
        }

        stage = Stage("test_stage", config)
        assert len(stage.templates[0]["sections"]) == 2

    def test_template_section_missing_id(self):
        """Test section without id fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [{"title": "Section 1", "level": 1}],  # Missing id
                }
            ],
        }

        with pytest.raises(ValueError, match="missing required 'id' field"):
            Stage("test_stage", config)

    def test_template_section_missing_title(self):
        """Test section without title fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [{"id": "section1", "level": 1}],  # Missing title
                }
            ],
        }

        with pytest.raises(ValueError, match="missing required 'title' field"):
            Stage("test_stage", config)

    def test_template_section_missing_level(self):
        """Test section without level fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [
                        {"id": "section1", "title": "Section 1"}
                    ],  # Missing level
                }
            ],
        }

        with pytest.raises(ValueError, match="missing required 'level' field"):
            Stage("test_stage", config)

    def test_template_section_invalid_level(self):
        """Test section with invalid level fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [
                        {"id": "section1", "title": "Section 1", "level": 7}
                    ],  # Invalid level
                }
            ],
        }

        with pytest.raises(ValueError, match="invalid level 7"):
            Stage("test_stage", config)

    def test_template_section_duplicate_ids(self):
        """Test duplicate section IDs fail validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [
                        {"id": "duplicate", "title": "Section 1", "level": 1},
                        {"id": "duplicate", "title": "Section 2", "level": 1},
                    ],
                }
            ],
        }

        with pytest.raises(ValueError, match="Duplicate section ID 'duplicate'"):
            Stage("test_stage", config)

    def test_template_nested_sections(self):
        """Test nested sections are validated correctly."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "sections": [
                        {
                            "id": "parent",
                            "title": "Parent Section",
                            "level": 1,
                            "subsections": [
                                {
                                    "id": "child",
                                    "title": "Child Section",
                                    "level": 2,
                                    "subsections": [
                                        {
                                            "id": "grandchild",
                                            "title": "Grandchild",
                                            "level": 3,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        stage = Stage("test_stage", config)
        assert len(stage.templates[0]["sections"]) == 1
        assert len(stage.templates[0]["sections"][0]["subsections"]) == 1
        assert (
            len(stage.templates[0]["sections"][0]["subsections"][0]["subsections"]) == 1
        )

    def test_template_too_many_warning(self):
        """Test warning is emitted for too many templates."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {"name": f"template_{i}", "description": f"Template {i}"}
                for i in range(6)
            ],
        }

        with pytest.warns(UserWarning, match="has 6 templates"):
            Stage("test_stage", config)

    def test_template_frontmatter_alignment_warning(self):
        """Test warning when template frontmatter doesn't align with expected_properties."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {"frontmatter.type": {"type": "str"}},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test",
                    "frontmatter": {
                        "other_field": "value"
                    },  # Missing 'type' from expected_properties
                }
            ],
        }

        with pytest.warns(
            UserWarning, match="missing expected frontmatter property 'type'"
        ):
            Stage("test_stage", config)


class TestActionTemplateReferences:
    """Test template reference validation in actions."""

    def test_action_template_reference_valid(self):
        """Test valid template reference in action."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [
                {"description": "Test action", "template": "test_template"}
            ],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"name": "test_template", "description": "Test template"}],
        }

        stage = Stage("test_stage", config)
        assert stage.stage_actions[0]["template"] == "test_template"

    def test_action_template_reference_invalid(self):
        """Test invalid template reference in action fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [
                {"description": "Test action", "template": "nonexistent_template"}
            ],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"name": "test_template", "description": "Test template"}],
        }

        with pytest.raises(
            ValueError, match="references unknown template 'nonexistent_template'"
        ):
            Stage("test_stage", config)

    def test_action_template_reference_empty(self):
        """Test empty template reference fails validation."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [{"description": "Test action", "template": ""}],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"name": "test_template", "description": "Test template"}],
        }

        with pytest.raises(
            ValueError, match="has invalid 'template' field: must be non-empty string"
        ):
            Stage("test_stage", config)

    def test_action_without_template_reference(self):
        """Test action without template reference works correctly."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [{"description": "Test action"}],
            "expected_properties": {},
            "is_final": False,
            "templates": [{"name": "test_template", "description": "Test template"}],
        }

        stage = Stage("test_stage", config)
        assert "template" not in stage.stage_actions[0]


class TestTemplateSerialization:
    """Test template serialization in to_dict()."""

    def test_templates_included_in_to_dict(self):
        """Test templates are included in to_dict() output."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [
                {
                    "name": "test_template",
                    "description": "Test template",
                    "frontmatter": {"type": "test"},
                }
            ],
        }

        stage = Stage("test_stage", config)
        stage_dict = stage.to_dict()

        assert "templates" in stage_dict
        assert len(stage_dict["templates"]) == 1
        assert stage_dict["templates"][0]["name"] == "test_template"

    def test_empty_templates_not_in_to_dict(self):
        """Test empty templates list is not included in to_dict() output."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
            "templates": [],
        }

        stage = Stage("test_stage", config)
        stage_dict = stage.to_dict()

        # Empty templates should not be included
        assert "templates" not in stage_dict

    def test_no_templates_field_in_to_dict(self):
        """Test stages without templates don't have templates field in to_dict()."""
        config: StageDefinition = {
            "name": "Test Stage",
            "description": "Test",
            "gates": [],
            "expected_actions": [],
            "expected_properties": {},
            "is_final": False,
        }

        stage = Stage("test_stage", config)
        stage_dict = stage.to_dict()

        assert "templates" not in stage_dict
