"""JSON schema loader for StageFlow."""

import json
from pathlib import Path

from stageflow.core.process import Process
from stageflow.loaders.yaml_loader import YamlLoader


class JsonLoader:
    """
    JSON loader for StageFlow process definitions.

    Loads and parses JSON files containing process definitions,
    leveraging the YAML loader's parsing logic for consistency.
    """

    def __init__(self):
        """Initialize JSON loader."""
        self._yaml_loader = YamlLoader()

    def load_process(self, file_path: str) -> Process:
        """
        Load process from JSON file.

        Args:
            file_path: Path to JSON file containing process definition

        Returns:
            Process instance created from JSON definition

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON structure is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Process file not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("JSON file must contain an object at root level")

        return self._yaml_loader._parse_process(data)

    def load_process_from_string(self, json_content: str) -> Process:
        """
        Load process from JSON string.

        Args:
            json_content: JSON content as string

        Returns:
            Process instance created from JSON content

        Raises:
            ValueError: If JSON structure is invalid
        """
        data = json.loads(json_content)

        if not isinstance(data, dict):
            raise ValueError("JSON content must contain an object at root level")

        return self._yaml_loader._parse_process(data)

    def save_process(self, process: Process, file_path: str, indent: int = 2):
        """
        Save process to JSON file.

        Args:
            process: Process to save
            file_path: Path where to save the JSON file
            indent: JSON indentation level
        """
        data = self._yaml_loader._process_to_dict(process)

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
