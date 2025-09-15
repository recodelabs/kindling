"""Tests for bundle assembler module."""

import uuid
from datetime import datetime

import pytest
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.reference import Reference

from kindling.bundle_assembler import BundleAssembler
from kindling.utils.random_utils import SeededRandom


class TestBundleAssembler:
    """Test suite for BundleAssembler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.assembler = BundleAssembler()
        self.rng = SeededRandom(42)

        # Create sample resources
        self.patient = Patient(
            id="patient-123",
            gender="female",
            birthDate="1980-01-01"
        )

        self.condition = Condition(
            id="condition-456",
            subject=Reference(reference="Patient/patient-123"),
            code={"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]}
        )

        self.observation = Observation(
            id="obs-789",
            status="final",
            code={"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
            subject=Reference(reference="Patient/patient-123")
        )

    def test_create_transaction_bundle(self):
        """Test creating a transaction bundle."""
        resources = [self.patient, self.condition, self.observation]
        bundle = self.assembler.create_bundle(
            resources,
            bundle_type="transaction",
            request_method="POST"
        )

        assert bundle.type == "transaction"
        assert len(bundle.entry) == 3
        assert bundle.timestamp is not None

        # Check entries have request
        for entry in bundle.entry:
            assert entry.request is not None
            assert entry.request.method == "POST"
            assert entry.request.url is not None

    def test_create_collection_bundle(self):
        """Test creating a collection bundle."""
        resources = [self.patient, self.condition]
        bundle = self.assembler.create_bundle(
            resources,
            bundle_type="collection"
        )

        assert bundle.type == "collection"
        assert len(bundle.entry) == 2

        # Collection bundles shouldn't have request
        for entry in bundle.entry:
            assert entry.request is None

    def test_create_bundle_with_put_method(self):
        """Test creating bundle with PUT method."""
        resources = [self.patient]
        bundle = self.assembler.create_bundle(
            resources,
            bundle_type="transaction",
            request_method="PUT"
        )

        assert bundle.entry[0].request.method == "PUT"
        assert bundle.entry[0].request.url == "Patient/patient-123"

    def test_create_bundle_with_conditional_method(self):
        """Test creating bundle with conditional create."""
        resources = [self.patient]
        bundle = self.assembler.create_bundle(
            resources,
            bundle_type="transaction",
            request_method="CONDITIONAL"
        )

        assert bundle.entry[0].request.method == "POST"
        # URL should contain search parameter for conditional create
        assert "identifier=" in bundle.entry[0].request.url

    def test_create_bundle_with_urn_mapping(self):
        """Test creating bundle with URN mapping for POST."""
        resources = [self.patient, self.condition]
        urn_mapping = {
            "patient-123": "urn-uuid-abc",
            "condition-456": "urn-uuid-def"
        }

        bundle = self.assembler.create_bundle(
            resources,
            bundle_type="transaction",
            request_method="POST",
            urn_mapping=urn_mapping
        )

        # Check fullUrl uses URN
        assert bundle.entry[0].fullUrl == "urn:uuid:urn-uuid-abc"
        assert bundle.entry[1].fullUrl == "urn:uuid:urn-uuid-def"

        # Resources shouldn't have IDs for POST
        assert bundle.entry[0].resource.id is None
        assert bundle.entry[1].resource.id is None

    def test_create_multiple_bundles(self):
        """Test splitting resources into multiple bundles."""
        # Create many resources
        resources = []
        for i in range(25):
            patient = Patient(
                id=f"patient-{i}",
                gender="male",
                birthDate="1990-01-01"
            )
            resources.append(patient)

        bundles = self.assembler.create_bundles(
            resources,
            bundle_type="transaction",
            bundle_size=10
        )

        assert len(bundles) == 3  # 25 resources / 10 per bundle = 3 bundles
        assert len(bundles[0].entry) == 10
        assert len(bundles[1].entry) == 10
        assert len(bundles[2].entry) == 5

    def test_empty_resource_list(self):
        """Test handling empty resource list."""
        bundle = self.assembler.create_bundle(
            [],
            bundle_type="transaction"
        )

        assert bundle.type == "transaction"
        assert len(bundle.entry) == 0
        assert bundle.timestamp is not None

    def test_bundle_has_unique_id(self):
        """Test that each bundle has a unique ID."""
        bundle1 = self.assembler.create_bundle([self.patient])
        bundle2 = self.assembler.create_bundle([self.patient])

        assert bundle1.id != bundle2.id
        assert bundle1.id is not None
        assert bundle2.id is not None

    def test_resource_reference_updates(self):
        """Test that references are updated correctly for URN mapping."""
        # Create condition with reference to patient
        condition = Condition(
            id="condition-1",
            subject=Reference(reference="Patient/patient-123"),
            code={"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]}
        )

        urn_mapping = {
            "patient-123": "uuid-patient",
            "condition-1": "uuid-condition"
        }

        bundle = self.assembler.create_bundle(
            [self.patient, condition],
            bundle_type="transaction",
            request_method="POST",
            urn_mapping=urn_mapping
        )

        # Check that the reference was updated to URN
        condition_entry = bundle.entry[1]
        assert condition_entry.resource.subject.reference == "urn:uuid:uuid-patient"

    def test_invalid_bundle_type(self):
        """Test that invalid bundle type raises error."""
        with pytest.raises(ValueError):
            self.assembler.create_bundle(
                [self.patient],
                bundle_type="invalid"
            )

    def test_invalid_request_method(self):
        """Test that invalid request method raises error."""
        with pytest.raises(ValueError):
            self.assembler.create_bundle(
                [self.patient],
                bundle_type="transaction",
                request_method="INVALID"
            )

    def test_bundle_timestamp_format(self):
        """Test that bundle timestamp has correct format."""
        bundle = self.assembler.create_bundle([self.patient])

        # Timestamp should be ISO format
        timestamp = bundle.timestamp
        assert isinstance(timestamp, str)
        # Should parse as datetime
        datetime.fromisoformat(timestamp.replace('+00:00', ''))

    def test_preserve_resource_attributes(self):
        """Test that resource attributes are preserved in bundle."""
        patient = Patient(
            id="test-patient",
            gender="female",
            birthDate="1985-06-15",
            name=[{"given": ["Jane"], "family": "Doe"}],
            telecom=[{"system": "phone", "value": "555-1234"}]
        )

        bundle = self.assembler.create_bundle(
            [patient],
            bundle_type="collection"
        )

        bundled_patient = bundle.entry[0].resource
        assert bundled_patient.gender == "female"
        assert bundled_patient.birthDate == "1985-06-15"
        assert bundled_patient.name[0].given[0] == "Jane"
        assert bundled_patient.telecom[0].value == "555-1234"