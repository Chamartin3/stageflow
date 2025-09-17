"""Project initialization command for StageFlow CLI."""

from pathlib import Path
from typing import Any

import click

from stageflow.cli.utils import handle_error
from stageflow.process.schema.loaders.yaml import YamlLoader


@click.command()
@click.argument("project_name")
@click.option(
    "--template",
    "-t",
    type=click.Choice(["basic", "onboarding", "approval", "ecommerce"]),
    default="basic",
    help="Project template to use",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="File format for process definition",
)
@click.pass_context
def init_command(
    ctx: click.Context,
    project_name: str,
    template: str,
    output_dir: Path,
    format: str,
):
    """
    Initialize a new StageFlow project.

    PROJECT_NAME: Name of the project to create

    Example:
        stageflow init my-workflow --template=onboarding --format=yaml
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Determine output directory
        if output_dir is None:
            output_dir = Path.cwd() / project_name
        else:
            output_dir = output_dir / project_name

        # Create project directory
        output_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            click.echo(f"Creating project '{project_name}' in {output_dir}")

        # Generate process definition based on template
        process_data = _get_template_data(project_name, template)

        # Save process definition
        file_extension = "yaml" if format == "yaml" else "json"
        process_file = output_dir / f"process.{file_extension}"

        if format == "yaml":
            loader = YamlLoader()
            with open(process_file, "w", encoding="utf-8") as f:
                loader.yaml.dump(process_data, f)
        else:
            import json

            with open(process_file, "w", encoding="utf-8") as f:
                json.dump(process_data, f, indent=2)

        # Create example element file
        example_element = _get_example_element(template)
        element_file = output_dir / "example_element.json"
        with open(element_file, "w", encoding="utf-8") as f:
            import json

            json.dump(example_element, f, indent=2)

        # Create project structure
        (output_dir / "elements").mkdir(exist_ok=True)
        (output_dir / "outputs").mkdir(exist_ok=True)

        # Create README
        readme_content = _generate_readme(project_name, template, format)
        readme_file = output_dir / "README.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # Success message
        click.echo(f"✅ Project '{project_name}' created successfully!")
        click.echo(f"   Location: {output_dir}")
        click.echo(f"   Process: {process_file.name}")
        click.echo(f"   Example: {element_file.name}")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"   cd {project_name}")
        click.echo(f"   stageflow validate process.{file_extension}")
        click.echo(f"   stageflow evaluate process.{file_extension} example_element.json")

    except Exception as e:
        handle_error(e, verbose)
        ctx.exit(1)


def _get_template_data(project_name: str, template: str) -> dict[str, Any]:
    """Generate process data based on template."""
    if template == "onboarding":
        return {
            "name": f"{project_name}_onboarding",
            "stage_order": ["registration", "profile_setup", "verification", "activation"],
            "stages": {
                "registration": {
                    "gates": {
                        "basic_info": {
                            "logic": "and",
                            "locks": [
                                {"property": "email", "type": "exists"},
                                {"property": "password", "type": "exists"},
                            ],
                        },
                        "email_format": {
                            "logic": "and",
                            "locks": [
                                {"property": "email", "type": "regex", "value": r"^[^@]+@[^@]+\.[^@]+$"},
                            ],
                        }
                    },
                    "schema": {
                        "required_fields": ["email", "password"],
                        "field_types": {"email": "string", "password": "string"},
                    },
                },
                "profile_setup": {
                    "gates": {
                        "profile_complete": {
                            "logic": "and",
                            "locks": [
                                {"property": "profile.first_name", "type": "exists"},
                                {"property": "profile.last_name", "type": "exists"},
                                {"property": "profile.phone", "type": "exists"},
                            ],
                        }
                    },
                },
                "verification": {
                    "gates": {
                        "verified": {
                            "logic": "and",
                            "locks": [
                                {"property": "email_verified", "type": "equals", "value": True},
                                {"property": "phone_verified", "type": "equals", "value": True},
                            ],
                        }
                    },
                },
                "activation": {
                    "gates": {
                        "activated": {
                            "logic": "and",
                            "locks": [{"property": "status", "type": "equals", "value": "active"}],
                        }
                    },
                },
            },
        }

    elif template == "approval":
        return {
            "name": f"{project_name}_approval",
            "stage_order": ["draft", "review", "approval", "published"],
            "stages": {
                "draft": {
                    "gates": {
                        "content_ready": {
                            "logic": "and",
                            "locks": [
                                {"property": "title", "type": "exists"},
                                {"property": "content", "type": "exists"},
                                {"property": "author", "type": "exists"},
                            ],
                        }
                    },
                },
                "review": {
                    "gates": {
                        "reviewed": {
                            "logic": "and",
                            "locks": [
                                {"property": "reviewer", "type": "exists"},
                                {"property": "review_status", "type": "in_list", "value": ["approved", "rejected"]},
                            ],
                        }
                    },
                },
                "approval": {
                    "gates": {
                        "approved": {
                            "logic": "and",
                            "locks": [
                                {"property": "review_status", "type": "equals", "value": "approved"},
                                {"property": "approver", "type": "exists"},
                            ],
                        }
                    },
                },
                "published": {
                    "gates": {
                        "live": {
                            "logic": "and",
                            "locks": [{"property": "published_at", "type": "exists"}],
                        }
                    },
                },
            },
        }

    elif template == "ecommerce":
        return {
            "name": f"{project_name}_order",
            "stage_order": ["cart", "checkout", "payment", "fulfillment", "delivery"],
            "stages": {
                "cart": {
                    "gates": {
                        "has_items": {
                            "logic": "and",
                            "locks": [
                                {"property": "items", "type": "exists"},
                                {"property": "total_amount", "type": "greater_than", "value": 0},
                            ],
                        }
                    },
                },
                "checkout": {
                    "gates": {
                        "shipping_info": {
                            "logic": "and",
                            "locks": [
                                {"property": "shipping_address", "type": "exists"},
                                {"property": "billing_address", "type": "exists"},
                            ],
                        }
                    },
                },
                "payment": {
                    "gates": {
                        "payment_complete": {
                            "logic": "and",
                            "locks": [
                                {"property": "payment_method", "type": "exists"},
                                {"property": "payment_status", "type": "equals", "value": "completed"},
                            ],
                        }
                    },
                },
                "fulfillment": {
                    "gates": {
                        "shipped": {
                            "logic": "and",
                            "locks": [
                                {"property": "tracking_number", "type": "exists"},
                                {"property": "shipment_date", "type": "exists"},
                            ],
                        }
                    },
                },
                "delivery": {
                    "gates": {
                        "delivered": {
                            "logic": "and",
                            "locks": [{"property": "delivery_date", "type": "exists"}],
                        }
                    },
                },
            },
        }

    else:  # basic template
        return {
            "name": project_name,
            "stage_order": ["stage1", "stage2", "stage3"],
            "stages": {
                "stage1": {
                    "gates": {
                        "gate1": {
                            "logic": "and",
                            "locks": [{"property": "field1", "type": "exists"}],
                        }
                    },
                },
                "stage2": {
                    "gates": {
                        "gate2": {
                            "logic": "and",
                            "locks": [
                                {"property": "field1", "type": "exists"},
                                {"property": "field2", "type": "exists"},
                            ],
                        }
                    },
                },
                "stage3": {
                    "gates": {
                        "gate3": {
                            "logic": "and",
                            "locks": [{"property": "field3", "type": "equals", "value": "completed"}],
                        }
                    },
                },
            },
        }


def _get_example_element(template: str) -> dict[str, Any]:
    """Generate example element data based on template."""
    if template == "onboarding":
        return {
            "email": "user@example.com",
            "password": "secure123",
            "profile": {"first_name": "John", "last_name": "Doe"},
            "email_verified": False,
            "phone_verified": False,
        }

    elif template == "approval":
        return {
            "title": "Sample Document",
            "content": "This is a sample document for approval workflow.",
            "author": "John Doe",
            "review_status": "pending",
        }

    elif template == "ecommerce":
        return {
            "items": [{"id": "item1", "name": "Product A", "price": 29.99}],
            "total_amount": 29.99,
            "shipping_address": "123 Main St, City, State 12345",
            "payment_method": "credit_card",
        }

    else:  # basic template
        return {"field1": "value1", "field2": "value2"}


def _generate_readme(project_name: str, template: str, format: str) -> str:
    """Generate README content for the project."""
    return f"""# {project_name}

A StageFlow project created with the '{template}' template.

## Files

- `process.{format}` - Process definition
- `example_element.json` - Example element data for testing
- `elements/` - Directory for element data files
- `outputs/` - Directory for generated outputs

## Usage

### Validate Process
```bash
stageflow validate process.{format}
```

### Evaluate Element
```bash
stageflow evaluate process.{format} example_element.json
```

### Generate Visualization
```bash
stageflow visualize process.{format} --format=mermaid --output=diagram.md
```

## Next Steps

1. Customize the process definition in `process.{format}`
2. Create your own element data files in the `elements/` directory
3. Use the StageFlow CLI commands to validate and evaluate your processes

For more information, visit: https://github.com/stageflow/stageflow
"""
