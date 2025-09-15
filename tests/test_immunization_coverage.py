"""Tests for Immunization and Coverage functionality."""

import pytest
from kindling.resource_factory import ResourceFactory
from kindling.generator import Generator
from kindling.utils.random_utils import SeededRandom
from fhir.resources.immunization import Immunization
from fhir.resources.coverage import Coverage


class TestImmunizationFactory:
    """Test Immunization factory methods."""

    def test_create_immunization_basic(self):
        """Test creating a basic Immunization resource."""
        factory = ResourceFactory(SeededRandom(42))

        immunization_def = {
            "vaccine": {
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "140",
                "display": "Influenza, seasonal"
            },
            "status": "completed",
            "days_ago": 30
        }

        immunization = factory.create_immunization(
            patient_id="test-patient-123",
            immunization_def=immunization_def
        )

        assert isinstance(immunization, Immunization)
        assert immunization.status == "completed"
        assert immunization.vaccineCode.coding[0].system == "http://hl7.org/fhir/sid/cvx"
        assert immunization.vaccineCode.coding[0].code == "140"
        assert immunization.vaccineCode.coding[0].display == "Influenza, seasonal"
        assert immunization.patient.reference == "Patient/test-patient-123"

    def test_create_immunization_with_details(self):
        """Test creating an Immunization with additional details."""
        factory = ResourceFactory(SeededRandom(42))

        immunization_def = {
            "vaccine": {
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "208",
                "display": "COVID-19 vaccine, mRNA"
            },
            "status": "completed",
            "days_ago": 60,
            "doseNumber": 2,
            "lotNumber": "LOT123456",
            "site": {
                "code": "LA",
                "display": "Left arm"
            },
            "route": {
                "code": "IM",
                "display": "Intramuscular"
            },
            "performer": "Practitioner/nurse-001"
        }

        immunization = factory.create_immunization(
            patient_id="test-patient-456",
            immunization_def=immunization_def
        )

        assert immunization.lotNumber == "LOT123456"
        assert immunization.site.coding[0].code == "LA"
        assert immunization.route.coding[0].code == "IM"
        assert immunization.performer[0].actor.reference == "Practitioner/nurse-001"


class TestCoverageFactory:
    """Test Coverage factory methods."""

    def test_create_coverage_basic(self):
        """Test creating a basic Coverage resource."""
        factory = ResourceFactory(SeededRandom(42))

        coverage_def = {
            "status": "active",
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "EHCPOL",
                "display": "Extended healthcare"
            }
        }

        coverage = factory.create_coverage(
            patient_id="test-patient-123",
            coverage_def=coverage_def
        )

        assert isinstance(coverage, Coverage)
        assert coverage.status == "active"
        assert coverage.type.coding[0].code == "EHCPOL"
        assert coverage.beneficiary.reference == "Patient/test-patient-123"
        assert coverage.subscriber.reference == "Patient/test-patient-123"
        assert len(coverage.paymentBy) == 1
        assert coverage.paymentBy[0].party.reference == "Organization/default-insurance"

    def test_create_coverage_with_details(self):
        """Test creating a Coverage with additional details."""
        factory = ResourceFactory(SeededRandom(42))

        coverage_def = {
            "status": "active",
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "PUBLICPOL",
                "display": "Public healthcare policy"
            },
            "identifier": {
                "system": "http://insurance.example/policy",
                "value": "POL-12345"
            },
            "payor": "Organization/insurance-company",
            "period": {
                "start_days_ago": 365,
                "end_days_ago": 0
            },
            "relationship": "self"
        }

        coverage = factory.create_coverage(
            patient_id="test-patient-789",
            coverage_def=coverage_def
        )

        assert coverage.type.coding[0].code == "PUBLICPOL"
        assert coverage.identifier[0].value == "POL-12345"
        assert coverage.paymentBy[0].party.reference == "Organization/insurance-company"
        assert coverage.period.start is not None
        assert coverage.relationship.coding[0].code == "self"


class TestImmunizationCoverageGeneration:
    """Test Immunization and Coverage generation in Generator."""

    def test_immunization_generation(self):
        """Test generating Immunization resources."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {
                    "family": "Smith",
                    "given": ["John"]
                },
                "gender": "male",
                "birthDate": "1980-01-15"
            },
            "resources": {
                "rules": [
                    {
                        "when": {"condition": "true"},
                        "then": {
                            "immunizations": [
                                {
                                    "vaccine": {
                                        "system": "http://hl7.org/fhir/sid/cvx",
                                        "code": "140",
                                        "display": "Influenza"
                                    },
                                    "days_ago": 30
                                },
                                {
                                    "vaccine": {
                                        "system": "http://hl7.org/fhir/sid/cvx",
                                        "code": "208",
                                        "display": "COVID-19 mRNA"
                                    },
                                    "days_ago": 180,
                                    "qty": 2  # Two doses
                                }
                            ]
                        }
                    }
                ]
            }
        }

        generator = Generator(profile=profile, seed=42)
        bundle = generator.generate(request_method="PUT")

        # Extract resources
        resources = [entry.resource for entry in bundle.entry]
        immunizations = [r for r in resources if r.resource_type == "Immunization"]

        assert len(immunizations) == 3  # 1 flu + 2 COVID

        # Check vaccine types
        flu_shots = [i for i in immunizations if i.vaccineCode.coding[0].code == "140"]
        covid_shots = [i for i in immunizations if i.vaccineCode.coding[0].code == "208"]

        assert len(flu_shots) == 1
        assert len(covid_shots) == 2

    def test_coverage_generation(self):
        """Test generating Coverage resources."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {
                    "family": "Doe",
                    "given": ["Jane"]
                },
                "gender": "female",
                "birthDate": "1975-05-20"
            },
            "resources": {
                "rules": [
                    {
                        "when": {"condition": "true"},
                        "then": {
                            "coverage": [
                                {
                                    "type": {
                                        "code": "EHCPOL",
                                        "display": "Extended healthcare"
                                    },
                                    "status": "active",
                                    "payor": "Organization/blue-cross"
                                },
                                {
                                    "type": {
                                        "code": "DENTPOL",
                                        "display": "Dental policy"
                                    },
                                    "status": "active",
                                    "payor": "Organization/dental-insurance"
                                }
                            ]
                        }
                    }
                ]
            }
        }

        generator = Generator(profile=profile, seed=42)
        bundle = generator.generate(request_method="PUT")

        # Extract resources
        resources = [entry.resource for entry in bundle.entry]
        coverages = [r for r in resources if r.resource_type == "Coverage"]

        assert len(coverages) == 2

        # Check coverage types
        health_coverage = [c for c in coverages if c.type.coding[0].code == "EHCPOL"][0]
        dental_coverage = [c for c in coverages if c.type.coding[0].code == "DENTPOL"][0]

        assert health_coverage.paymentBy[0].party.reference == "Organization/blue-cross"
        assert dental_coverage.paymentBy[0].party.reference == "Organization/dental-insurance"

    def test_complete_persona_with_immunizations_and_coverage(self):
        """Test a complete persona with both immunizations and coverage."""
        # Test with Grace's TB persona
        generator = Generator.from_persona('grace_tb')
        bundle = generator.generate(request_method="PUT")

        # Extract resources
        resources = [entry.resource for entry in bundle.entry]
        immunizations = [r for r in resources if r.resource_type == "Immunization"]
        coverages = [r for r in resources if r.resource_type == "Coverage"]

        # Check immunizations exist
        assert len(immunizations) > 0

        # Check for BCG vaccine (TB patient should have this)
        bcg_vaccines = [i for i in immunizations if i.vaccineCode.coding[0].code == "19"]
        assert len(bcg_vaccines) == 1

        # Check coverage exists
        assert len(coverages) == 1
        coverage = coverages[0]
        assert coverage.status == "active"
        assert "NHIF" in coverage.identifier[0].value  # Kenya's national insurance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])