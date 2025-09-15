"""Tests for profile parser module."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from kindling.profile_parser import ProfileParser, ProfileSchema


class TestProfileParser:
    """Test suite for ProfileParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ProfileParser()
        self.valid_profile = {
            "version": "0.1",
            "mode": "cohort",
            "demographics": {
                "age": {"min": 18, "max": 90},
                "gender": {
                    "distribution": {"male": 0.5, "female": 0.5}
                }
            },
            "resources": {
                "include": ["Patient", "Condition", "Observation"],
                "rules": [
                    {
                        "name": "diabetes",
                        "when": {"condition": "age > 50"},
                        "then": {
                            "add_conditions": [
                                {
                                    "code": {
                                        "system": "http://snomed.info/sct",
                                        "value": "44054006",
                                        "display": "Type 2 diabetes mellitus"
                                    },
                                    "onset": {"years_ago": 5}
                                }
                            ]
                        }
                    }
                ]
            }
        }

    def test_parse_yaml_profile(self):
        """Test parsing a YAML profile file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.valid_profile, f)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path)
            assert result["version"] == "0.1"
            assert result["mode"] == "cohort"
            assert "demographics" in result
            assert "resources" in result
        finally:
            Path(temp_path).unlink()

    def test_parse_json_profile(self):
        """Test parsing a JSON profile file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_profile, f)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path)
            assert result["version"] == "0.1"
            assert result["mode"] == "cohort"
            assert "demographics" in result
            assert "resources" in result
        finally:
            Path(temp_path).unlink()

    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file raises ValueError."""
        with pytest.raises(ValueError, match="Profile file not found"):
            self.parser.parse("/nonexistent/file.yaml")

    def test_parse_unsupported_format(self):
        """Test parsing unsupported file format raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                self.parser.parse(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # yaml.YAMLError or similar
                self.parser.parse(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json content}')
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # json.JSONDecodeError
                self.parser.parse(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validate_valid_profile(self):
        """Test validating a valid profile."""
        assert self.parser.validate(self.valid_profile) == True

    def test_validate_invalid_mode(self):
        """Test validating profile with invalid mode."""
        invalid_profile = self.valid_profile.copy()
        invalid_profile["mode"] = "invalid_mode"

        with pytest.raises(ValueError, match="Invalid profile"):
            self.parser.validate(invalid_profile)

    def test_single_patient_mode(self):
        """Test profile with single patient mode."""
        single_profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"given": ["John"], "family": "Doe"},
                "gender": "male",
                "birthDate": "1980-01-01"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(single_profile, f)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path)
            assert result["mode"] == "single"
            assert "single_patient" in result
        finally:
            Path(temp_path).unlink()

    def test_default_values(self):
        """Test that default values are applied."""
        minimal_profile = {"version": "0.1"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(minimal_profile, f)
            temp_path = f.name

        try:
            result = self.parser.parse(temp_path)
            assert result["mode"] == "cohort"  # Default mode
            assert result["demographics"] == {}
            assert result["resources"] == {}
            assert result["output"] == {}
        finally:
            Path(temp_path).unlink()


class TestProfileSchema:
    """Test suite for ProfileSchema."""

    def test_schema_validation(self):
        """Test basic schema validation."""
        schema = ProfileSchema(
            version="0.1",
            mode="cohort",
            demographics={"age": {"min": 18, "max": 90}}
        )
        assert schema.version == "0.1"
        assert schema.mode == "cohort"

    def test_invalid_mode_pattern(self):
        """Test that invalid mode pattern raises validation error."""
        with pytest.raises(ValidationError):
            ProfileSchema(mode="invalid")

    def test_default_factory(self):
        """Test that default factories work correctly."""
        schema = ProfileSchema()
        assert schema.demographics == {}
        assert schema.single_patient == {}
        assert schema.resources == {}
        assert schema.output == {}