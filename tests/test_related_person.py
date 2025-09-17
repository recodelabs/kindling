"""Tests for RelatedPerson functionality."""

import pytest
from kindling.resource_factory import ResourceFactory
from kindling.generator import Generator
from kindling.utils.random_utils import SeededRandom
from fhir.resources.patient import Patient
from fhir.resources.relatedperson import RelatedPerson


class TestRelatedPersonFactory:
    """Test RelatedPerson factory methods."""

    def test_create_related_person_basic(self):
        """Test creating a basic RelatedPerson resource."""
        factory = ResourceFactory(SeededRandom(42))

        related_def = {
            "name": {
                "family": "Smith",
                "given": ["John"]
            },
            "relationship": "parent",
            "gender": "male",
            "birthDate": "1960-05-15"
        }

        related_person = factory.create_related_person(
            patient_id="test-patient-123",
            related_person_def=related_def
        )

        assert isinstance(related_person, RelatedPerson)
        assert related_person.name[0].family == "Smith"
        assert related_person.name[0].given == ["John"]
        assert related_person.patient.reference == "Patient/test-patient-123"
        assert related_person.relationship[0].coding[0].code == "PRN"
        assert related_person.relationship[0].coding[0].display == "parent"
        assert related_person.gender == "male"
        assert str(related_person.birthDate) == "1960-05-15"
        assert related_person.active is True

    def test_create_related_person_with_identifiers(self):
        """Test creating a RelatedPerson with identifiers."""
        factory = ResourceFactory(SeededRandom(42))

        related_def = {
            "name": {
                "family": "Doe",
                "given": ["Jane"]
            },
            "relationship": "spouse",
            "identifiers": [
                {
                    "system": "http://example.org/mrn",
                    "value": "MRN-12345",
                    "use": "official"
                }
            ]
        }

        related_person = factory.create_related_person(
            patient_id="test-patient-456",
            related_person_def=related_def
        )

        assert related_person.identifier[0].system == "http://example.org/mrn"
        assert related_person.identifier[0].value == "MRN-12345"
        assert related_person.identifier[0].use == "official"
        assert related_person.relationship[0].coding[0].code == "SPS"

    def test_create_related_person_with_contact_info(self):
        """Test creating a RelatedPerson with contact information."""
        factory = ResourceFactory(SeededRandom(42))

        related_def = {
            "name": {
                "family": "Johnson",
                "given": ["Emily"]
            },
            "relationship": "child",
            "phone": "+1-555-1234",
            "email": "emily.johnson@example.com"
        }

        related_person = factory.create_related_person(
            patient_id="test-patient-789",
            related_person_def=related_def
        )

        assert len(related_person.telecom) == 2
        phone_contact = [t for t in related_person.telecom if t.system == "phone"][0]
        email_contact = [t for t in related_person.telecom if t.system == "email"][0]

        assert phone_contact.value == "+1-555-1234"
        assert email_contact.value == "emily.johnson@example.com"
        assert related_person.relationship[0].coding[0].code == "CHILD"

    def test_relationship_mapping(self):
        """Test all relationship type mappings."""
        factory = ResourceFactory(SeededRandom(42))

        relationship_tests = [
            ("parent", "PRN", "parent"),
            ("child", "CHILD", "child"),
            ("spouse", "SPS", "spouse"),
            ("sibling", "SIB", "sibling"),
            ("guardian", "GUARD", "guardian"),
            ("emergency", "C", "emergency contact")
        ]

        for relationship, expected_code, expected_display in relationship_tests:
            related_def = {
                "name": {"family": "Test", "given": ["Person"]},
                "relationship": relationship
            }

            related_person = factory.create_related_person(
                patient_id="test-patient",
                related_person_def=related_def
            )

            assert related_person.relationship[0].coding[0].code == expected_code
            assert related_person.relationship[0].coding[0].display == expected_display


class TestSymmetricalRelatedPersons:
    """Test symmetrical RelatedPerson creation in Generator."""

    def test_symmetrical_related_persons_creation(self):
        """Test creating symmetrical RelatedPerson resources."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {
                    "family": "Berg",
                    "given": ["Matt"]
                },
                "gender": "male",
                "birthDate": "1985-01-15"
            },
            "resources": {
                "rules": [
                    {
                        "when": {"condition": "true"},
                        "then": {
                            "related_persons": [
                                {
                                    "name": {
                                        "family": "Berg",
                                        "given": ["Anouk"]
                                    },
                                    "relationship": "child",
                                    "gender": "female",
                                    "birthDate": "2015-06-20"
                                }
                            ]
                        }
                    }
                ]
            }
        }

        generator = Generator(profile=profile, seed=42)
        # Generate with PUT request method to keep resource IDs
        bundle = generator.generate(request_method="PUT")

        # Extract resources from bundle
        resources = [entry.resource for entry in bundle.entry]

        # Check we have correct number and types of resources
        patients = [r for r in resources if r.resource_type == "Patient"]
        related_persons = [r for r in resources if r.resource_type == "RelatedPerson"]

        assert len(patients) == 2  # Main patient + related patient
        assert len(related_persons) == 2  # Two symmetrical RelatedPerson resources

        # Find the main patient (Matt)
        main_patient = [p for p in patients if p.name[0].given == ["Matt"]][0]
        # Find the related patient (Anouk)
        related_patient = [p for p in patients if p.name[0].given == ["Anouk"]][0]

        # Find RelatedPerson resources
        # One should link Anouk as child of Matt
        child_relation = None
        parent_relation = None

        for rp in related_persons:
            # Check if this RelatedPerson is linked to Matt
            if rp.patient.reference == f"Patient/{main_patient.id}":
                # This RelatedPerson is linked to Matt
                child_relation = rp
            # Check if this RelatedPerson is linked to Anouk
            elif rp.patient.reference == f"Patient/{related_patient.id}":
                # This RelatedPerson is linked to Anouk
                parent_relation = rp

        assert child_relation is not None
        assert parent_relation is not None

        # Verify child relation (Anouk as child of Matt)
        assert child_relation.name[0].given == ["Anouk"]
        assert child_relation.relationship[0].coding[0].code == "CHILD"
        assert child_relation.gender == "female"

        # Verify parent relation (Matt as parent of Anouk)
        assert parent_relation.name[0].given == ["Matt"]
        assert parent_relation.relationship[0].coding[0].code == "PRN"  # parent
        assert parent_relation.gender == "male"

        # Verify identifiers link to the respective Patient resources
        assert len(child_relation.identifier) > 0
        assert child_relation.identifier[0].value == related_patient.id

        assert len(parent_relation.identifier) > 0
        assert parent_relation.identifier[0].value == main_patient.id

    def test_symmetrical_related_persons_preserve_identifiers(self):
        """Ensure custom identifiers are preserved when creating symmetrical RelatedPersons."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {
                    "family": "Doe",
                    "given": ["Alex"]
                },
                "gender": "male",
                "birthDate": "1980-04-01"
            },
            "resources": {
                "rules": [
                    {
                        "when": {"condition": "true"},
                        "then": {
                            "related_persons": [
                                {
                                    "name": {
                                        "family": "Doe",
                                        "given": ["Jamie"]
                                    },
                                    "relationship": "child",
                                    "gender": "female",
                                    "birthDate": "2010-07-15",
                                    "identifiers": [
                                        {
                                            "system": "http://example.org/mrn",
                                            "value": "CHILD-123"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }

        generator = Generator(profile=profile, seed=123)
        bundle = generator.generate(request_method="PUT")

        resources = [entry.resource for entry in bundle.entry]
        patients = [r for r in resources if r.resource_type == "Patient"]
        related_persons = [r for r in resources if r.resource_type == "RelatedPerson"]

        assert len(patients) == 2
        assert len(related_persons) == 2

        main_patient = [p for p in patients if p.name[0].given == ["Alex"]][0]
        child_patient = [p for p in patients if p.name[0].given == ["Jamie"]][0]

        child_relation = [
            rp for rp in related_persons
            if rp.patient.reference == f"Patient/{main_patient.id}"
        ][0]

        identifier_values = {ident.value for ident in child_relation.identifier}
        assert "CHILD-123" in identifier_values
        assert child_patient.id in identifier_values

    def test_multiple_related_persons(self):
        """Test creating multiple related persons."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {
                    "family": "Smith",
                    "given": ["John"]
                },
                "gender": "male",
                "birthDate": "1980-03-10"
            },
            "resources": {
                "rules": [
                    {
                        "when": {"condition": "true"},
                        "then": {
                            "related_persons": [
                                {
                                    "name": {
                                        "family": "Smith",
                                        "given": ["Jane"]
                                    },
                                    "relationship": "spouse",
                                    "gender": "female",
                                    "birthDate": "1982-07-15"
                                },
                                {
                                    "name": {
                                        "family": "Smith",
                                        "given": ["Alice"]
                                    },
                                    "relationship": "child",
                                    "gender": "female",
                                    "birthDate": "2010-09-20"
                                }
                            ]
                        }
                    }
                ]
            }
        }

        generator = Generator(profile=profile, seed=42)
        # Generate with PUT request method to keep resource IDs
        bundle = generator.generate(request_method="PUT")

        # Extract resources
        resources = [entry.resource for entry in bundle.entry]
        patients = [r for r in resources if r.resource_type == "Patient"]
        related_persons = [r for r in resources if r.resource_type == "RelatedPerson"]

        # Should have 3 patients (main + 2 related)
        assert len(patients) == 3
        # Should have 4 RelatedPerson resources (2 symmetrical pairs)
        assert len(related_persons) == 4

        # Verify we have the expected relationships
        relationships = [rp.relationship[0].coding[0].code for rp in related_persons]
        # Should have spouse-spouse and parent-child pairs
        assert "SPS" in relationships  # spouse
        assert "CHILD" in relationships  # child
        assert "PRN" in relationships  # parent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])