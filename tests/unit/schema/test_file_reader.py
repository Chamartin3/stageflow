import json

import pytest

from stageflow.schema.loader import FileReader, LoadError


class TestFileReader:
    def test_read_yaml_file_success(self, tmp_path):
        """Test successful YAML file reading."""
        """Test successful YAML file reading."""
        yaml_content = "key: value\nlist:\n  - 1\n"
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        data = FileReader.read_file(yaml_file)
        assert isinstance(data, dict)
        assert data["key"] == "value"
        assert data["list"] == [1]

    def test_read_json_file_success(self, tmp_path):
        """Test successful JSON file reading."""
        json_content = {"key": "value", "list": [1, 2, 3]}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(json_content))
        data = FileReader.read_file(json_file)
        assert data == json_content

    def test_file_not_found_error(self):
        """Test FileReader raises LoadError for missing files."""
        with pytest.raises(LoadError, match="File not found"):
            FileReader.read_file("non_existent_file.yaml")

    def test_unsupported_format_error(self, tmp_path):
        """Test FileReader raises LoadError for unsupported extensions."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        with pytest.raises(LoadError, match="Unsupported file format"):
            FileReader.read_file(txt_file)

    def test_invalid_yaml_syntax_error(self, tmp_path):
        """Test FileReader handles invalid YAML with specific error message."""
        invalid_yaml = "key: [unclosed"
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(invalid_yaml)
        with pytest.raises(LoadError, match="Error parsing YAML"):
            FileReader.read_file(yaml_file)

    def test_invalid_json_syntax_error(self, tmp_path):
        """Test FileReader handles invalid JSON with specific error message."""
        invalid_json = '{"key": [}'
        json_file = tmp_path / "invalid.json"
        json_file.write_text(invalid_json)
        with pytest.raises(LoadError, match="Error parsing JSON"):
            FileReader.read_file(json_file)

    def test_permission_denied_error(self, tmp_path):
        """Test FileReader handles permission errors."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")
        yaml_file.chmod(0)
        try:
            with pytest.raises(LoadError, match="Permission denied"):
                FileReader.read_file(yaml_file)
        finally:
            yaml_file.chmod(0o644)

    def test_encoding_error(self, tmp_path, monkeypatch):
        """Test FileReader handles encoding errors."""
        file_path = tmp_path / "test.yaml"
        file_path.write_text("key: value")

        def fake_open(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "reason")

        monkeypatch.setattr("builtins.open", fake_open)
        with pytest.raises(LoadError, match="Encoding error"):
            FileReader.read_file(file_path)
