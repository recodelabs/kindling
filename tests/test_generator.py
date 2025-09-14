"""Tests for the Generator class."""

import pytest
from kindling import Generator
from kindling.persona_loader import PersonaLoader


def test_generator_from_persona():
    """Test creating generator from persona."""
    gen = Generator.from_persona("mary_diabetes", seed=42)
    assert gen is not None
    assert gen.persona_name == "mary_diabetes"
    assert gen.seed == 42


def test_generator_from_profile():
    """Test creating generator from profile dictionary."""
    profile = {
        "version": "0.1",
        "mode": "single",
        "single_patient": {
            "name": {
                "family": "Test",
                "given": ["Patient"]
            },
            "gender": "male",
            "birthDate": "1990-01-01"
        },
        "resources": {
            "include": ["Patient"],
            "rules": []
        }
    }

    gen = Generator(profile=profile, seed=42)
    assert gen is not None
    assert gen.profile == profile


def test_generator_requires_profile_or_persona():
    """Test that generator requires either profile or persona."""
    with pytest.raises(ValueError, match="Must specify either profile or persona"):
        Generator()


def test_generator_cannot_have_both():
    """Test that generator cannot have both profile and persona."""
    profile = {"version": "0.1"}
    with pytest.raises(ValueError, match="Cannot specify both profile and persona"):
        Generator(profile=profile, persona="mary_diabetes")


def test_single_patient_generation():
    """Test generating a single patient."""
    profile = {
        "version": "0.1",
        "mode": "single",
        "single_patient": {
            "name": {
                "family": "Test",
                "given": ["Patient"]
            },
            "gender": "male",
            "birthDate": "1990-01-01"
        },
        "resources": {
            "include": ["Patient"],
            "rules": []
        }
    }

    gen = Generator(profile=profile, seed=42)
    bundle = gen.generate()

    assert bundle is not None
    assert bundle.type == "transaction"
    assert len(bundle.entry) > 0


def test_cohort_generation():
    """Test generating a cohort of patients."""
    profile = {
        "version": "0.1",
        "mode": "cohort",
        "demographics": {
            "age": {"min": 30, "max": 50},
            "gender": {
                "distribution": {
                    "male": 0.5,
                    "female": 0.5
                }
            }
        },
        "resources": {
            "include": ["Patient"],
            "rules": []
        }
    }

    gen = Generator(profile=profile, seed=42)
    bundles = gen.generate(count=5)

    assert bundles is not None