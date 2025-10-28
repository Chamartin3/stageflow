import json
from pathlib import Path

import pytest

from stageflow.element import Element
from stageflow.schema.loader import LoadError, load_element


class TestLoadElement:
    def test_load_element_success(self, tmp_path):
        """Test successful element loading from JSON file."""
        data = {"foo": 1, "bar": {"baz": "qux"}}
        file_path = tmp_path / "element.json"
        file_path.write_text(json.dumps(data))
        element = load_element(file_path)
        assert isinstance(element, Element)
        assert element.to_dict() == data

    def test_load_element_returns_element_instance(self, tmp_path):
        """Test load_element returns Element instance, not dict."""
        data = {"key": "value"}
        file_path = tmp_path / "element.json"
        file_path.write_text(json.dumps(data))
        element = load_element(file_path)
        assert not isinstance(element, dict)
        assert isinstance(element, Element)

    def test_load_element_with_nested_data(self, tmp_path):
        """Test load_element works with complex nested data."""
        data = {"nested": {"list": [1, {"inner": "value"}]}, "value": 42}
        file_path = tmp_path / "element.json"
        file_path.write_text(json.dumps(data))
        element = load_element(file_path)
        assert isinstance(element, Element)
        assert element.to_dict() == data

    def test_load_element_file_not_found(self):
        """Test load_element raises LoadError for missing files."""
        non_existent = Path("/tmp/non_existent_file.json")
        with pytest.raises(LoadError, match="File not found"):
            load_element(non_existent)

    def test_load_element_invalid_json(self, tmp_path):
        """Test load_element handles invalid JSON syntax."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{invalid_json: }")
        with pytest.raises(LoadError, match="Error parsing JSON"):
            load_element(file_path)

    def test_load_element_non_dict_data(self, tmp_path):
        """Test load_element handles non-dictionary data."""
        file_path = tmp_path / "array.json"
        file_path.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(LoadError, match="Element data must be a dictionary"):
            load_element(file_path)

    def test_load_element_element_validation_error(self, tmp_path, monkeypatch):
        """Test load_element chains Element validation errors."""
        data = {"foo": "bar"}
        file_path = tmp_path / "element.json"
        file_path.write_text(json.dumps(data))

        def fake_create_element(_):
            raise ValueError("validation failed")

        monkeypatch.setattr(
            "stageflow.schema.loader.create_element", fake_create_element
        )
        with pytest.raises(LoadError, match="Element validation failed"):
            load_element(file_path)

    def test_load_element_error_chaining(self, tmp_path, monkeypatch):
        """Test load_element properly chains underlying errors."""
        data = {"foo": "bar"}
        file_path = tmp_path / "element.json"
        file_path.write_text(json.dumps(data))

        def fake_create_element(_):
            raise RuntimeError("underlying error")

        monkeypatch.setattr(
            "stageflow.schema.loader.create_element", fake_create_element
        )
        with pytest.raises(LoadError) as excinfo:
            load_element(file_path)
        assert excinfo.value.__cause__ is not None
