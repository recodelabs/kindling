"""Tests for personas."""

import pytest
from kindling.persona_loader import PersonaLoader


def test_list_personas():
    """Test listing available personas."""
    loader = PersonaLoader()
    personas = loader.list_personas()

    assert "mary_diabetes" in personas
    assert "john_asthma" in personas
    assert "linda_hypertension" in personas
    assert "david_healthy" in personas


def test_load_mary_persona():
    """Test loading Mary diabetes persona."""
    loader = PersonaLoader()
    data = loader.load("mary_diabetes")

    assert data is not None
    assert data["name"] == "mary_diabetes"
    assert data["patient"]["gender"] == "female"
    assert data["patient"]["name"]["family"] == "Jones"


def test_load_nonexistent_persona():
    """Test loading non-existent persona raises error."""
    loader = PersonaLoader()
    with pytest.raises(ValueError, match="Persona 'nonexistent' not found"):
        loader.load("nonexistent")


def test_persona_caching():
    """Test that personas are cached after first load."""
    loader = PersonaLoader()

    # Load once
    data1 = loader.load("mary_diabetes")

    # Load again (should come from cache)
    data2 = loader.load("mary_diabetes")

    assert data1 is data2  # Same object reference