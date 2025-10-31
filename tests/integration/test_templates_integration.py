"""Integration tests for stage templates in complete processes."""

from stageflow.element import create_element
from stageflow.process import Process


class TestTemplatesIntegration:
    """Test templates integrated with complete processes."""

    def test_process_with_templates_loads_correctly(self):
        """Test a process with templates loads and evaluates correctly."""
        process_config = {
            "name": "Bug Tracking",
            "description": "Bug reporting and resolution workflow",
            "initial_stage": "reported",
            "final_stage": "resolved",
            "stages": {
                "reported": {
                    "name": "Bug Reported",
                    "expected_properties": {
                        "frontmatter": {
                            "type": {"type": "str"},
                            "severity": {"type": "str"},
                        },
                        "description": {"type": "str"},
                    },
                    "templates": [
                        {
                            "name": "bug_report",
                            "description": "Template for documenting a new bug",
                            "parameters": [
                                {
                                    "name": "severity",
                                    "required": True,
                                    "description": "Bug severity level",
                                    "placeholder": "critical|high|medium|low",
                                }
                            ],
                            "frontmatter": {
                                "type": "bug",
                                "status": "reported",
                                "severity": "{severity}",
                            },
                            "sections": [
                                {
                                    "id": "description",
                                    "title": "Description",
                                    "level": 1,
                                    "content": "Provide a clear description of the bug.",
                                },
                                {
                                    "id": "steps",
                                    "title": "Steps to Reproduce",
                                    "level": 1,
                                    "content": "1. [First step]\n2. [Second step]\n3. [See error]",
                                },
                            ],
                        }
                    ],
                    "expected_actions": [
                        {
                            "name": "document_bug",
                            "description": "Document the bug with complete information",
                            "template": "bug_report",
                            "instructions": [
                                "Set severity level",
                                "Provide clear description",
                                "Add reproduction steps",
                            ],
                        }
                    ],
                    "gates": [
                        {
                            "name": "start_investigation",
                            "target_stage": "investigating",
                            "locks": [
                                {"exists": "frontmatter.severity"},
                                {"exists": "description"},
                            ],
                        }
                    ],
                },
                "investigating": {
                    "name": "Investigating",
                    "gates": [
                        {
                            "name": "mark_resolved",
                            "target_stage": "resolved",
                            "locks": [{"exists": "resolution"}],
                        }
                    ],
                },
                "resolved": {"name": "Resolved", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)

        # Verify templates are loaded
        reported_stage = process.get_stage("reported")
        assert len(reported_stage.templates) == 1
        assert reported_stage.templates[0]["name"] == "bug_report"
        assert len(reported_stage.templates[0]["parameters"]) == 1
        assert len(reported_stage.templates[0]["sections"]) == 2

        # Verify action template reference
        assert reported_stage.stage_actions[0]["template"] == "bug_report"

    def test_process_evaluates_with_templates(self):
        """Test process evaluation works correctly with templates present."""
        process_config = {
            "name": "Simple Workflow",
            "description": "Test workflow with templates",
            "initial_stage": "draft",
            "final_stage": "published",
            "stages": {
                "draft": {
                    "name": "Draft",
                    "templates": [
                        {
                            "name": "article_template",
                            "description": "Template for new article",
                            "frontmatter": {"type": "article", "status": "draft"},
                            "sections": [
                                {
                                    "id": "introduction",
                                    "title": "Introduction",
                                    "level": 1,
                                }
                            ],
                        }
                    ],
                    "expected_actions": [
                        {
                            "description": "Write draft content",
                            "template": "article_template",
                        }
                    ],
                    "gates": [
                        {
                            "name": "submit_for_review",
                            "target_stage": "published",
                            "locks": [{"exists": "content"}],
                        }
                    ],
                },
                "published": {"name": "Published", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)

        # Test evaluation with missing content
        element = create_element(
            {"frontmatter": {"type": "article", "status": "draft"}}
        )
        result = process.evaluate(element, "draft")

        assert result["stage_result"].status.value == "action_required"

        # Test evaluation with content (ready for transition)
        element_complete = create_element(
            {
                "frontmatter": {"type": "article", "status": "draft"},
                "content": "Article content here",
            }
        )
        result = process.evaluate(element_complete, "draft")

        assert result["stage_result"].status.value == "ready"

    def test_nested_sections_template(self):
        """Test templates with deeply nested sections."""
        process_config = {
            "name": "Design Document",
            "description": "Technical design workflow",
            "initial_stage": "design",
            "final_stage": "approved",
            "stages": {
                "design": {
                    "name": "Design",
                    "templates": [
                        {
                            "name": "design_doc",
                            "description": "Complete design document template",
                            "sections": [
                                {
                                    "id": "overview",
                                    "title": "Overview",
                                    "level": 1,
                                    "content": "High-level overview",
                                },
                                {
                                    "id": "architecture",
                                    "title": "Architecture",
                                    "level": 1,
                                    "subsections": [
                                        {
                                            "id": "components",
                                            "title": "Components",
                                            "level": 2,
                                            "subsections": [
                                                {
                                                    "id": "backend",
                                                    "title": "Backend",
                                                    "level": 3,
                                                },
                                                {
                                                    "id": "frontend",
                                                    "title": "Frontend",
                                                    "level": 3,
                                                },
                                            ],
                                        },
                                        {
                                            "id": "data_model",
                                            "title": "Data Model",
                                            "level": 2,
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                    "gates": [
                        {
                            "name": "approve_design",
                            "target_stage": "approved",
                            "locks": [{"exists": "approved"}],
                        }
                    ],
                },
                "approved": {"name": "Approved", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)
        design_stage = process.get_stage("design")

        # Verify nested structure
        template = design_stage.templates[0]
        assert len(template["sections"]) == 2
        assert len(template["sections"][1]["subsections"]) == 2
        assert len(template["sections"][1]["subsections"][0]["subsections"]) == 2

    def test_multiple_templates_per_stage(self):
        """Test stage with multiple templates."""
        process_config = {
            "name": "Development Process",
            "description": "Software development workflow",
            "initial_stage": "specification",
            "final_stage": "deployed",
            "stages": {
                "specification": {
                    "name": "Specification",
                    "templates": [
                        {
                            "name": "feature_spec",
                            "description": "Template for feature specifications",
                            "frontmatter": {"type": "feature", "complexity": "medium"},
                            "sections": [
                                {
                                    "id": "requirements",
                                    "title": "Requirements",
                                    "level": 1,
                                },
                                {"id": "design", "title": "Design", "level": 1},
                            ],
                        },
                        {
                            "name": "simple_spec",
                            "description": "Template for simple changes",
                            "frontmatter": {"type": "feature", "complexity": "low"},
                            "sections": [
                                {
                                    "id": "description",
                                    "title": "Description",
                                    "level": 1,
                                }
                            ],
                        },
                    ],
                    "expected_actions": [
                        {
                            "description": "Create detailed specification",
                            "template": "feature_spec",
                        },
                        {
                            "description": "Create simple specification",
                            "template": "simple_spec",
                        },
                    ],
                    "gates": [
                        {
                            "name": "start_development",
                            "target_stage": "deployed",
                            "locks": [{"exists": "spec_complete"}],
                        }
                    ],
                },
                "deployed": {"name": "Deployed", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)
        spec_stage = process.get_stage("specification")

        # Verify both templates are loaded
        assert len(spec_stage.templates) == 2
        assert spec_stage.templates[0]["name"] == "feature_spec"
        assert spec_stage.templates[1]["name"] == "simple_spec"

        # Verify both actions reference their templates
        assert spec_stage.stage_actions[0]["template"] == "feature_spec"
        assert spec_stage.stage_actions[1]["template"] == "simple_spec"

    def test_template_with_all_optional_fields(self):
        """Test template with parameters, frontmatter, and sections."""
        process_config = {
            "name": "Review Process",
            "description": "Code review workflow",
            "initial_stage": "review",
            "final_stage": "approved",
            "stages": {
                "review": {
                    "name": "Review",
                    "templates": [
                        {
                            "name": "review_checklist",
                            "description": "Code review checklist template",
                            "parameters": [
                                {
                                    "name": "reviewer_name",
                                    "required": True,
                                    "description": "Name of reviewer",
                                    "placeholder": "John Doe",
                                },
                                {
                                    "name": "pr_number",
                                    "required": True,
                                    "description": "Pull request number",
                                    "placeholder": "123",
                                },
                            ],
                            "frontmatter": {
                                "type": "review",
                                "reviewer": "{reviewer_name}",
                                "pr": "{pr_number}",
                            },
                            "sections": [
                                {
                                    "id": "code_quality",
                                    "title": "Code Quality",
                                    "level": 1,
                                    "content": "- [ ] Code follows style guidelines\n- [ ] Variables are well-named",
                                },
                                {
                                    "id": "testing",
                                    "title": "Testing",
                                    "level": 1,
                                    "content": "- [ ] Tests cover new functionality\n- [ ] Tests pass",
                                },
                            ],
                        }
                    ],
                    "expected_actions": [
                        {
                            "description": "Conduct code review",
                            "template": "review_checklist",
                        }
                    ],
                    "gates": [
                        {
                            "name": "approve_review",
                            "target_stage": "approved",
                            "locks": [{"exists": "review_complete"}],
                        }
                    ],
                },
                "approved": {"name": "Approved", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)
        review_stage = process.get_stage("review")
        template = review_stage.templates[0]

        # Verify all fields are present
        assert len(template["parameters"]) == 2
        assert "frontmatter" in template
        assert len(template["frontmatter"]) == 3
        assert len(template["sections"]) == 2
        assert "content" in template["sections"][0]

    def test_template_parameter_placeholders(self):
        """Test that parameter placeholders are preserved in template."""
        process_config = {
            "name": "Task Workflow",
            "description": "Task management",
            "initial_stage": "planning",
            "final_stage": "done",
            "stages": {
                "planning": {
                    "name": "Planning",
                    "templates": [
                        {
                            "name": "task_template",
                            "description": "Template for new tasks",
                            "parameters": [
                                {
                                    "name": "task_name",
                                    "required": True,
                                    "description": "Name of the task",
                                    "placeholder": "Implement feature X",
                                }
                            ],
                            "frontmatter": {"title": "{task_name}", "status": "todo"},
                        }
                    ],
                    "gates": [
                        {
                            "name": "start_task",
                            "target_stage": "done",
                            "locks": [{"exists": "completed"}],
                        }
                    ],
                },
                "done": {"name": "Done", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)
        template = process.get_stage("planning").templates[0]

        # Verify placeholder is preserved in frontmatter
        assert template["frontmatter"]["title"] == "{task_name}"

        # Verify parameter placeholder is set
        assert template["parameters"][0]["placeholder"] == "Implement feature X"

    def test_process_to_dict_preserves_templates(self):
        """Test that process serialization preserves templates."""
        process_config = {
            "name": "Test Process",
            "description": "Process with templates",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": {
                "start": {
                    "name": "Start",
                    "templates": [
                        {
                            "name": "test_template",
                            "description": "Test",
                            "frontmatter": {"type": "test"},
                        }
                    ],
                    "gates": [
                        {
                            "name": "complete",
                            "target_stage": "end",
                            "locks": [{"exists": "done"}],
                        }
                    ],
                },
                "end": {"name": "End", "is_final": True, "gates": []},
            },
        }

        process = Process(process_config)
        process_dict = process.to_dict()

        # Verify templates are in serialized output
        assert "templates" in process_dict["stages"]["start"]
        assert len(process_dict["stages"]["start"]["templates"]) == 1
        assert (
            process_dict["stages"]["start"]["templates"][0]["name"] == "test_template"
        )
