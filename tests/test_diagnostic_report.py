"""Tests for DiagnosticReport functionality."""

import pytest
from kindling.resource_factory import ResourceFactory
from kindling.generator import Generator
from kindling.utils.random_utils import SeededRandom
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.observation import Observation


class TestDiagnosticReportFactory:
    """Test DiagnosticReport factory methods."""

    def test_create_diagnostic_report_basic(self):
        """Test creating a basic DiagnosticReport resource."""
        factory = ResourceFactory(SeededRandom(42))

        report_def = {
            "code": {
                "system": "http://loinc.org",
                "value": "24323-8",
                "display": "Comprehensive metabolic panel"
            },
            "status": "final",
            "conclusion": "All values within normal limits",
            "days_ago": 7
        }

        report = factory.create_diagnostic_report(
            patient_id="test-patient-123",
            diagnostic_report_def=report_def
        )

        assert isinstance(report, DiagnosticReport)
        assert report.status == "final"
        assert report.code.coding[0].system == "http://loinc.org"
        assert report.code.coding[0].code == "24323-8"
        assert report.code.coding[0].display == "Comprehensive metabolic panel"
        assert report.subject.reference == "Patient/test-patient-123"
        assert report.conclusion == "All values within normal limits"
        assert report.category[0].coding[0].code == "LAB"

    def test_create_diagnostic_report_with_observations(self):
        """Test creating a DiagnosticReport with observation references."""
        factory = ResourceFactory(SeededRandom(42))

        report_def = {
            "code": {
                "system": "http://loinc.org",
                "value": "24331-1",
                "display": "Lipid panel"
            },
            "status": "final"
        }

        observation_refs = [
            "Observation/obs-1",
            "Observation/obs-2",
            "Observation/obs-3"
        ]

        report = factory.create_diagnostic_report(
            patient_id="test-patient-456",
            diagnostic_report_def=report_def,
            observation_refs=observation_refs
        )

        assert len(report.result) == 3
        assert report.result[0].reference == "Observation/obs-1"
        assert report.result[1].reference == "Observation/obs-2"
        assert report.result[2].reference == "Observation/obs-3"

    def test_create_diagnostic_report_with_category(self):
        """Test creating a DiagnosticReport with custom category."""
        factory = ResourceFactory(SeededRandom(42))

        report_def = {
            "code": {
                "system": "http://loinc.org",
                "value": "123456",
                "display": "Test Report"
            },
            "category": {
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "RAD",
                "display": "Radiology"
            },
            "status": "preliminary"
        }

        report = factory.create_diagnostic_report(
            patient_id="test-patient-789",
            diagnostic_report_def=report_def
        )

        assert report.category[0].coding[0].code == "RAD"
        assert report.category[0].coding[0].display == "Radiology"
        assert report.status == "preliminary"


class TestDiagnosticReportGeneration:
    """Test DiagnosticReport generation in Generator."""

    def test_diagnostic_report_with_observations_generation(self):
        """Test generating DiagnosticReport with associated Observations."""
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
                            "diagnostic_reports": [
                                {
                                    "code": {
                                        "system": "http://loinc.org",
                                        "value": "24323-8",
                                        "display": "Comprehensive metabolic panel"
                                    },
                                    "status": "final",
                                    "conclusion": "Normal metabolic panel",
                                    "observations": [
                                        {
                                            "loinc": "2345-7",
                                            "display": "Glucose",
                                            "range": {"min": 90, "max": 90},
                                            "unit": "mg/dL"
                                        },
                                        {
                                            "loinc": "2160-0",
                                            "display": "Creatinine",
                                            "range": {"min": 1.0, "max": 1.0},
                                            "unit": "mg/dL"
                                        }
                                    ]
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
        patients = [r for r in resources if r.resource_type == "Patient"]
        reports = [r for r in resources if r.resource_type == "DiagnosticReport"]
        observations = [r for r in resources if r.resource_type == "Observation"]

        assert len(patients) == 1
        assert len(reports) == 1
        assert len(observations) == 2

        # Check the report
        report = reports[0]
        assert report.code.coding[0].display == "Comprehensive metabolic panel"
        assert report.conclusion == "Normal metabolic panel"
        assert len(report.result) == 2  # Should reference 2 observations

        # Check observations
        glucose_obs = [o for o in observations if o.code.coding[0].code == "2345-7"][0]
        creatinine_obs = [o for o in observations if o.code.coding[0].code == "2160-0"][0]

        assert glucose_obs.code.coding[0].display == "Glucose"
        assert creatinine_obs.code.coding[0].display == "Creatinine"

    def test_multiple_diagnostic_reports(self):
        """Test generating multiple DiagnosticReports."""
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
                            "diagnostic_reports": [
                                {
                                    "code": {
                                        "system": "http://loinc.org",
                                        "value": "24323-8",
                                        "display": "CMP"
                                    },
                                    "status": "final",
                                    "days_ago": 30
                                },
                                {
                                    "code": {
                                        "system": "http://loinc.org",
                                        "value": "24331-1",
                                        "display": "Lipid panel"
                                    },
                                    "status": "final",
                                    "days_ago": 60
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
        reports = [r for r in resources if r.resource_type == "DiagnosticReport"]

        assert len(reports) == 2

        # Check both reports exist
        cmp_report = [r for r in reports if r.code.coding[0].code == "24323-8"][0]
        lipid_report = [r for r in reports if r.code.coding[0].code == "24331-1"][0]

        assert cmp_report.code.coding[0].display == "CMP"
        assert lipid_report.code.coding[0].display == "Lipid panel"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])