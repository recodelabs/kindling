"""Tests for FHIR bundle validation."""

import json
import pytest
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationrequest import MedicationRequest

from kindling import Generator
from kindling.bundle_assembler import BundleAssembler


class TestBundleValidation:
    """Test suite for validating generated FHIR bundles."""

    def test_bundle_is_valid_json(self):
        """Test that generated bundles are valid JSON."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        # Should be able to serialize to JSON without errors
        json_str = bundle.json(indent=2)
        assert json_str is not None

        # Should be able to parse back from JSON
        parsed = json.loads(json_str)
        assert parsed["resourceType"] == "Bundle"
        assert parsed["type"] == "transaction"
        assert "entry" in parsed
        assert isinstance(parsed["entry"], list)

    def test_bundle_structure_validation(self):
        """Test that bundle structure conforms to FHIR spec."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        # Validate bundle has required fields
        bundle_dict = bundle.dict()
        assert bundle_dict['resourceType'] == "Bundle"
        assert bundle.type in ["transaction", "collection", "document", "message", "history", "searchset", "batch"]
        assert bundle.id is not None
        assert bundle.timestamp is not None

        # Validate entries
        assert bundle.entry is not None
        assert len(bundle.entry) > 0

        for entry in bundle.entry:
            # Each entry should have a resource
            assert entry.resource is not None
            assert entry.fullUrl is not None

            # Transaction bundles should have request
            if bundle.type == "transaction":
                assert entry.request is not None
                assert entry.request.method in ["GET", "POST", "PUT", "DELETE", "PATCH"]
                assert entry.request.url is not None

    def test_resource_validation(self):
        """Test that individual resources in bundle are valid."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        resource_types = set()
        for entry in bundle.entry:
            resource = entry.resource
            resource_types.add(resource.__class__.__name__)

            # Common resource validations
            # In transaction bundles, resources use URNs in fullUrl instead of ids
            assert entry.fullUrl is not None
            assert entry.fullUrl.startswith("urn:uuid:")

            # Resource-specific validations
            if isinstance(resource, Patient):
                self._validate_patient(resource)
            elif isinstance(resource, Condition):
                self._validate_condition(resource)
            elif isinstance(resource, Observation):
                self._validate_observation(resource)
            elif isinstance(resource, MedicationRequest):
                self._validate_medication_request(resource)

        # Mary should have specific resource types
        assert "Patient" in resource_types
        assert "Condition" in resource_types
        assert "Observation" in resource_types
        assert "MedicationRequest" in resource_types

    def _validate_patient(self, patient: Patient):
        """Validate Patient resource."""
        assert patient.dict()['resourceType'] == "Patient"
        assert patient.name is not None and len(patient.name) > 0
        assert patient.gender in ["male", "female", "other", "unknown"]
        assert patient.birthDate is not None

        # Mary specific validations
        if patient.name[0].family == "Jones":
            assert patient.gender == "female"
            assert patient.name[0].given == ["Mary", "Elizabeth"]

    def _validate_condition(self, condition: Condition):
        """Validate Condition resource."""
        assert condition.dict()['resourceType'] == "Condition"
        assert condition.code is not None
        assert condition.subject is not None
        assert condition.subject.reference is not None
        assert condition.clinicalStatus is not None
        assert condition.verificationStatus is not None

    def _validate_observation(self, observation: Observation):
        """Validate Observation resource."""
        assert observation.dict()['resourceType'] == "Observation"
        assert observation.status in ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]
        assert observation.code is not None
        assert observation.subject is not None

        # If it has a value, validate it
        if observation.valueQuantity:
            assert observation.valueQuantity.value is not None
            assert observation.valueQuantity.unit is not None

    def _validate_medication_request(self, med_request: MedicationRequest):
        """Validate MedicationRequest resource."""
        assert med_request.dict()['resourceType'] == "MedicationRequest"
        assert med_request.status in ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"]
        assert med_request.intent in ["proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"]
        assert med_request.medication is not None
        assert med_request.subject is not None

    def test_reference_integrity(self):
        """Test that references between resources are valid."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        # Collect all resource URNs (transaction bundles use URNs)
        resource_urns = set()
        patient_urn = None

        for entry in bundle.entry:
            resource = entry.resource
            # In transaction bundles, resources are identified by URNs
            resource_urns.add(entry.fullUrl)

            if isinstance(resource, Patient):
                patient_urn = entry.fullUrl

        assert patient_urn is not None

        # Check that all references point to existing resources
        for entry in bundle.entry:
            resource = entry.resource

            # Check subject references
            if hasattr(resource, "subject") and resource.subject:
                ref = resource.subject.reference
                # Should reference the patient URN in transaction bundles
                assert ref == patient_urn

    def test_persona_consistency(self):
        """Test that generated data is consistent with persona definition."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        # Find conditions
        conditions = []
        observations = []
        medications = []

        for entry in bundle.entry:
            resource = entry.resource
            if isinstance(resource, Condition):
                conditions.append(resource)
            elif isinstance(resource, Observation):
                observations.append(resource)
            elif isinstance(resource, MedicationRequest):
                medications.append(resource)

        # Mary should have diabetes
        diabetes_codes = ["44054006"]  # Type 2 diabetes SNOMED code
        has_diabetes = any(
            any(coding.code in diabetes_codes for coding in cond.code.coding)
            for cond in conditions
        )
        assert has_diabetes, "Mary persona should have Type 2 diabetes condition"

        # Should have medications for diabetes
        diabetes_meds = ["860975"]  # metformin RxNorm code
        has_diabetes_med = any(
            any(coding.code in diabetes_meds for coding in med.medication.concept.coding)
            for med in medications
        )
        assert has_diabetes_med, "Mary persona should have metformin prescription"

        # Should have HbA1c observations
        hba1c_codes = ["4548-4"]  # HbA1c LOINC code
        has_hba1c = any(
            any(coding.code in hba1c_codes for coding in obs.code.coding)
            for obs in observations
        )
        assert has_hba1c, "Mary persona should have HbA1c observations"

    def test_multiple_personas(self):
        """Test that different personas generate different data."""
        # Generate Mary
        gen_mary = Generator.from_persona("mary_diabetes", seed=42)
        bundle_mary = gen_mary.generate()

        # Generate John
        gen_john = Generator.from_persona("john_asthma", seed=42)
        bundle_john = gen_john.generate()

        # Extract patient names
        mary_patient = None
        john_patient = None

        for entry in bundle_mary.entry:
            if isinstance(entry.resource, Patient):
                mary_patient = entry.resource
                break

        for entry in bundle_john.entry:
            if isinstance(entry.resource, Patient):
                john_patient = entry.resource
                break

        assert mary_patient is not None
        assert john_patient is not None

        # Should have different demographics
        assert mary_patient.name[0].family == "Jones"
        assert john_patient.name[0].family == "Smith"
        assert mary_patient.gender == "female"
        assert john_patient.gender == "male"

    def test_deterministic_generation(self):
        """Test that same seed produces same output."""
        # Generate twice with same seed
        gen1 = Generator.from_persona("mary_diabetes", seed=42)
        bundle1 = gen1.generate()

        gen2 = Generator.from_persona("mary_diabetes", seed=42)
        bundle2 = gen2.generate()

        # Should produce identical bundles (except for timestamps)
        assert len(bundle1.entry) == len(bundle2.entry)

        # Check patient IDs are the same
        patient1_id = None
        patient2_id = None

        for entry in bundle1.entry:
            if isinstance(entry.resource, Patient):
                patient1_id = entry.resource.id
                break

        for entry in bundle2.entry:
            if isinstance(entry.resource, Patient):
                patient2_id = entry.resource.id
                break

        assert patient1_id == patient2_id

    def test_bundle_can_be_parsed_by_fhir_resources(self):
        """Test that generated bundle can be parsed back using fhir.resources."""
        gen = Generator.from_persona("mary_diabetes", seed=42)
        bundle = gen.generate()

        # Serialize to JSON
        json_str = bundle.json(indent=2)

        # Parse back using fhir.resources
        parsed_bundle = Bundle.parse_raw(json_str)

        assert parsed_bundle is not None
        assert parsed_bundle.dict()['resourceType'] == "Bundle"
        assert len(parsed_bundle.entry) == len(bundle.entry)

        # Validate each entry can be parsed
        for entry in parsed_bundle.entry:
            assert entry.resource is not None
            assert entry.fullUrl is not None