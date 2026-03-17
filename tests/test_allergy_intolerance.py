"""Tests for AllergyIntolerance resource generation."""

import pytest
from fhir.resources.allergyintolerance import AllergyIntolerance

from kindling import Generator
from kindling.resource_factory import ResourceFactory
from kindling.utils.random_utils import SeededRandom


class TestAllergyIntoleranceFactory:
    """Test AllergyIntolerance creation in ResourceFactory."""

    def setup_method(self):
        self.rng = SeededRandom(42)
        self.factory = ResourceFactory(self.rng)

    def test_create_allergy_intolerance(self):
        """Should create a valid AllergyIntolerance resource."""
        allergy_def = {
            "code": {
                "system": "http://snomed.info/sct",
                "value": "91936005",
                "display": "Penicillin allergy",
            },
            "criticality": "high",
            "type": "allergy",
        }

        allergy = self.factory.create_allergy_intolerance(
            patient_id="patient-1",
            allergy_def=allergy_def,
            allergy_id="allergy-1",
        )

        assert isinstance(allergy, AllergyIntolerance)
        assert allergy.id == "allergy-1"
        assert allergy.code.coding[0].code == "91936005"
        assert allergy.code.coding[0].display == "Penicillin allergy"
        assert allergy.patient.reference == "Patient/patient-1"
        assert allergy.clinicalStatus.coding[0].code == "active"

    def test_create_allergy_with_patient_ref(self):
        """Should use custom patient reference when provided."""
        allergy_def = {
            "code": {
                "system": "http://snomed.info/sct",
                "value": "232346004",
                "display": "Cat allergy",
            },
            "criticality": "low",
            "type": "allergy",
        }

        allergy = self.factory.create_allergy_intolerance(
            patient_id="patient-1",
            allergy_def=allergy_def,
            patient_ref="urn:uuid:abc-123",
        )

        assert allergy.patient.reference == "urn:uuid:abc-123"


class TestAllergyIntoleranceGenerator:
    """Test that the generator handles allergies in rules."""

    def test_allergies_generated_from_persona(self):
        """Allergies defined in a profile should produce AllergyIntolerance resources."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["Allergy"]},
                "gender": "female",
                "birthDate": "1962-11-08",
            },
            "resources": {
                "include": ["Patient", "AllergyIntolerance"],
                "rules": [
                    {
                        "name": "allergies",
                        "when": {"condition": "true"},
                        "then": {
                            "allergies": [
                                {
                                    "code": {
                                        "system": "http://snomed.info/sct",
                                        "value": "232346004",
                                        "display": "Cat allergy",
                                    },
                                    "criticality": "low",
                                    "type": "allergy",
                                },
                                {
                                    "code": {
                                        "system": "http://snomed.info/sct",
                                        "value": "91936005",
                                        "display": "Penicillin allergy",
                                    },
                                    "criticality": "high",
                                    "type": "allergy",
                                },
                            ]
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        allergies = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "AllergyIntolerance"
        ]

        assert len(allergies) == 2
        displays = {a.code.coding[0].display for a in allergies}
        assert "Cat allergy" in displays
        assert "Penicillin allergy" in displays
