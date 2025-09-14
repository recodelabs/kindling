"""Loader for built-in personas."""

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


class PersonaLoader:
    """Loader for built-in personas."""

    def __init__(self):
        """Initialize persona loader."""
        self.personas_dir = Path(__file__).parent / "personas"
        self._personas_cache = {}

    def load(self, persona_name: str) -> Dict[str, Any]:
        """Load a built-in persona.

        Args:
            persona_name: Name of the persona to load

        Returns:
            Persona data dictionary

        Raises:
            ValueError: If persona not found
        """
        # Check cache
        if persona_name in self._personas_cache:
            return self._personas_cache[persona_name]

        # Look for persona file
        persona_file = self.personas_dir / f"{persona_name}.yaml"
        if not persona_file.exists():
            persona_file = self.personas_dir / f"{persona_name}.json"

        if not persona_file.exists():
            available = self.list_personas()
            raise ValueError(
                f"Persona '{persona_name}' not found. "
                f"Available personas: {', '.join(available)}"
            )

        # Load persona data
        with open(persona_file, 'r') as f:
            if persona_file.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Cache and return
        self._personas_cache[persona_name] = data
        return data

    def list_personas(self) -> List[str]:
        """List available personas.

        Returns:
            List of persona names
        """
        personas = []

        if self.personas_dir.exists():
            for file in self.personas_dir.glob("*.yaml"):
                personas.append(file.stem)
            for file in self.personas_dir.glob("*.json"):
                if file.stem not in personas:
                    personas.append(file.stem)

        return sorted(personas)