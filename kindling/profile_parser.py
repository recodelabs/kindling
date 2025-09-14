"""Parser for YAML/JSON profiles."""

import json
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import BaseModel, Field, ValidationError


class ProfileSchema(BaseModel):
    """Schema for validating profiles."""

    version: str = Field(default="0.1")
    mode: str = Field(default="cohort", pattern="^(cohort|single)$")
    demographics: Dict[str, Any] = Field(default_factory=dict)
    single_patient: Dict[str, Any] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)


class ProfileParser:
    """Parser for profile files."""

    def parse(self, profile_path: Union[str, Path]) -> Dict[str, Any]:
        """Parse a profile file.

        Args:
            profile_path: Path to YAML or JSON profile file

        Returns:
            Parsed and validated profile dictionary

        Raises:
            ValueError: If profile is invalid
        """
        profile_path = Path(profile_path)

        if not profile_path.exists():
            raise ValueError(f"Profile file not found: {profile_path}")

        # Load file content
        with open(profile_path, 'r') as f:
            if profile_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif profile_path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {profile_path.suffix}")

        # Validate profile
        try:
            profile = ProfileSchema(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid profile: {e}")

        return profile.model_dump()

    def validate(self, profile_dict: Dict[str, Any]) -> bool:
        """Validate a profile dictionary.

        Args:
            profile_dict: Profile dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If profile is invalid
        """
        try:
            ProfileSchema(**profile_dict)
            return True
        except ValidationError as e:
            raise ValueError(f"Invalid profile: {e}")