"""Tests for MedicationStatement resource generation."""

import pytest
from fhir.resources.medicationstatement import MedicationStatement

from kindling import Generator
from kindling.resource_factory import ResourceFactory
from kindling.utils.random_utils import SeededRandom


class TestMedicationStatementFactory:
    """Test MedicationStatement creation in ResourceFactory."""

    def setup_method(self):
        self.rng = SeededRandom(42)
        self.factory = ResourceFactory(self.rng)

    def test_create_medication_statement(self):
        """Should create a valid MedicationStatement resource."""
        med_def = {
            "rxnorm": "314077",
            "display": "lisinopril 20 MG Oral Tablet",
            "sig": "Take 1 tablet by mouth daily",
            "status": "recorded",
        }

        med_stmt = self.factory.create_medication_statement(
            patient_id="patient-1",
            medication_def=med_def,
            medication_id="medstmt-1",
        )

        assert isinstance(med_stmt, MedicationStatement)
        assert med_stmt.id == "medstmt-1"
        assert med_stmt.status == "recorded"
        assert med_stmt.medication.concept.coding[0].code == "314077"
        assert med_stmt.medication.concept.coding[0].display == "lisinopril 20 MG Oral Tablet"
        assert med_stmt.subject.reference == "Patient/patient-1"

    def test_create_medication_statement_with_encounter(self):
        """Should include encounter reference when provided."""
        med_def = {
            "rxnorm": "314077",
            "display": "lisinopril 20 MG Oral Tablet",
            "sig": "Take 1 tablet by mouth daily",
        }

        med_stmt = self.factory.create_medication_statement(
            patient_id="patient-1",
            medication_def=med_def,
            encounter_ref="Encounter/enc-1",
        )

        assert med_stmt.encounter.reference == "Encounter/enc-1"

    def test_create_medication_statement_default_status(self):
        """Default status should be 'recorded'."""
        med_def = {
            "rxnorm": "314077",
            "display": "lisinopril 20 MG Oral Tablet",
        }

        med_stmt = self.factory.create_medication_statement(
            patient_id="patient-1",
            medication_def=med_def,
        )

        assert med_stmt.status == "recorded"


class TestMedicationStatementGenerator:
    """Test that the generator handles medication_statements in rules."""

    def test_medication_statements_generated(self):
        """medication_statements in a rule should produce MedicationStatement resources."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["Meds"]},
                "gender": "female",
                "birthDate": "1962-11-08",
            },
            "resources": {
                "include": ["Patient", "MedicationStatement"],
                "rules": [
                    {
                        "name": "meds",
                        "when": {"condition": "true"},
                        "then": {
                            "medication_statements": [
                                {
                                    "rxnorm": "314077",
                                    "display": "lisinopril 20 MG Oral Tablet",
                                    "sig": "Take 1 tablet by mouth daily",
                                },
                                {
                                    "rxnorm": "617312",
                                    "display": "atorvastatin 40 MG Oral Tablet",
                                    "sig": "Take 1 tablet daily at bedtime",
                                },
                            ]
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        med_stmts = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "MedicationStatement"
        ]

        assert len(med_stmts) == 2
        displays = {m.medication.concept.coding[0].display for m in med_stmts}
        assert "lisinopril 20 MG Oral Tablet" in displays
        assert "atorvastatin 40 MG Oral Tablet" in displays
