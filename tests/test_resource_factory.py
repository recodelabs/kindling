"""Tests for resource factory module."""

from datetime import datetime, timedelta

import pytest
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.encounter import Encounter

from kindling.resource_factory import ResourceFactory
from kindling.utils.random_utils import SeededRandom


class TestResourceFactory:
    """Test suite for ResourceFactory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rng = SeededRandom(42)
        self.factory = ResourceFactory(self.rng)

    def test_create_patient_with_full_data(self):
        """Test creating a patient with complete data."""
        patient_def = {
            "name": {
                "given": ["John", "Michael"],
                "family": "Smith"
            },
            "gender": "male",
            "birthDate": "1980-05-15",
            "identifiers": [
                {
                    "system": "http://hospital.example/mrn",
                    "value": "MRN-12345"
                }
            ],
            "address": {
                "line": ["123 Main St"],
                "city": "Boston",
                "state": "MA",
                "postalCode": "02134",
                "country": "US"
            },
            "telecom": [
                {
                    "system": "phone",
                    "value": "555-1234",
                    "use": "home"
                },
                {
                    "system": "email",
                    "value": "john@example.com",
                    "use": "home"
                }
            ]
        }

        patient = self.factory.create_patient(patient_def, "patient-123")

        assert isinstance(patient, Patient)
        assert patient.id == "patient-123"
        assert patient.gender == "male"
        assert patient.birthDate == "1980-05-15"
        assert patient.name[0].given[0] == "John"
        assert patient.name[0].given[1] == "Michael"
        assert patient.name[0].family == "Smith"
        assert patient.identifier[0].value == "MRN-12345"
        assert patient.address[0].city == "Boston"
        assert len(patient.telecom) == 2

    def test_create_patient_with_minimal_data(self):
        """Test creating a patient with minimal data."""
        patient_def = {
            "gender": "female"
        }

        patient = self.factory.create_patient(patient_def)

        assert isinstance(patient, Patient)
        assert patient.id is not None
        assert patient.gender == "female"
        # Should have default name
        assert patient.name[0].family == "Doe"
        # Should have default MRN
        assert len(patient.identifier) == 1
        assert "MRN-" in patient.identifier[0].value

    def test_create_patient_without_id(self):
        """Test that patient ID is generated if not provided."""
        patient_def = {"gender": "male"}
        patient = self.factory.create_patient(patient_def)

        assert patient.id is not None
        assert len(patient.id) > 0

    def test_create_condition(self):
        """Test creating a condition resource."""
        condition_def = {
            "code": {
                "system": "http://snomed.info/sct",
                "value": "44054006",
                "display": "Type 2 diabetes mellitus"
            },
            "onset": {
                "years_ago": 5
            }
        }

        condition = self.factory.create_condition(
            patient_id="patient-123",
            condition_def=condition_def,
            condition_id="condition-456"
        )

        assert isinstance(condition, Condition)
        assert condition.id == "condition-456"
        assert condition.subject.reference == "Patient/patient-123"
        assert condition.code.coding[0].code == "44054006"
        assert condition.clinicalStatus.coding[0].code == "active"
        assert condition.verificationStatus.coding[0].code == "confirmed"

        # Check onset date is approximately 5 years ago
        onset_date = datetime.strptime(condition.onsetDateTime, "%Y-%m-%d")
        expected_date = datetime.now() - timedelta(days=5 * 365)
        date_diff = abs((onset_date - expected_date).days)
        assert date_diff < 2  # Allow 1-2 days difference

    def test_create_condition_with_patient_ref(self):
        """Test creating condition with custom patient reference."""
        condition_def = {
            "code": {
                "system": "http://snomed.info/sct",
                "value": "38341003",
                "display": "Hypertension"
            }
        }

        condition = self.factory.create_condition(
            patient_id="patient-123",
            condition_def=condition_def,
            patient_ref="urn:uuid:abc-def-ghi"
        )

        assert condition.subject.reference == "urn:uuid:abc-def-ghi"

    def test_create_observation(self):
        """Test creating an observation resource."""
        obs_def = {
            "loinc": "4548-4",
            "display": "Hemoglobin A1c",
            "range": {
                "min": 6.5,
                "max": 9.0
            },
            "unit": "%"
        }

        observation = self.factory.create_observation(
            patient_id="patient-123",
            observation_def=obs_def,
            observation_id="obs-789"
        )

        assert isinstance(observation, Observation)
        assert observation.id == "obs-789"
        assert observation.status == "final"
        assert observation.code.coding[0].code == "4548-4"
        assert observation.subject.reference == "Patient/patient-123"

        # Check value is within specified range
        value = observation.valueQuantity.value
        assert 6.5 <= value <= 9.0
        assert observation.valueQuantity.unit == "%"

    def test_create_observation_with_fixed_value(self):
        """Test creating observation with fixed value."""
        obs_def = {
            "loinc": "2339-0",
            "display": "Glucose",
            "value": 120,
            "unit": "mg/dL"
        }

        observation = self.factory.create_observation(
            patient_id="patient-123",
            observation_def=obs_def
        )

        assert observation.valueQuantity.value == 120
        assert observation.valueQuantity.unit == "mg/dL"

    def test_create_observation_boolean(self):
        """Boolean observations should populate valueBoolean."""

        obs_def = {
            "loinc": "618-9",
            "display": "Mycobacterium tuberculosis culture",
            "value_type": "boolean",
            "positive": True,
        }

        event_time = datetime.now() - timedelta(days=5)
        observation = self.factory.create_observation(
            patient_id="patient-123",
            observation_def=obs_def,
            observation_id="obs-boolean",
            effective_datetime=event_time,
        )

        assert observation.valueBoolean is True
        expected = self.factory._format_datetime(event_time)
        effective_value = observation.effectiveDateTime
        observed = effective_value.isoformat() if hasattr(effective_value, "isoformat") else effective_value
        assert observed == expected
        assert not hasattr(observation, "valueQuantity") or observation.valueQuantity is None

    def test_create_medication_request(self):
        """Test creating a medication request."""
        med_def = {
            "rxnorm": "860975",
            "display": "metformin 1000 MG Oral Tablet",
            "sig": "Take 1 tablet by mouth twice daily",
            "frequency": 2
        }

        med_request = self.factory.create_medication_request(
            patient_id="patient-123",
            medication_def=med_def,
            medication_id="med-456"
        )

        assert isinstance(med_request, MedicationRequest)
        assert med_request.id == "med-456"
        assert med_request.status == "active"
        assert med_request.intent == "order"
        assert med_request.subject.reference == "Patient/patient-123"
        assert med_request.medication.concept.coding[0].code == "860975"
        assert med_request.dosageInstruction[0].text == "Take 1 tablet by mouth twice daily"
        assert med_request.dosageInstruction[0].timing["repeat"]["frequency"] == 2

    def test_create_medication_request_with_prn(self):
        """Test creating PRN medication (frequency < 1)."""
        med_def = {
            "rxnorm": "123456",
            "display": "Pain medication",
            "sig": "Take as needed for pain",
            "frequency": 0.5  # PRN
        }

        med_request = self.factory.create_medication_request(
            patient_id="patient-123",
            medication_def=med_def
        )

        # Frequency should be normalized to 1 for PRN
        assert med_request.dosageInstruction[0].timing["repeat"]["frequency"] == 1

    def test_create_medication_request_with_duration(self):
        """Medication requests honor duration and completion fields."""

        med_def = {
            "rxnorm": "198332",
            "display": "pyridoxine 25 MG Oral Tablet",
            "sig": "Take 1 tablet daily",
            "frequency": 1,
            "status": "completed",
            "duration_days": 30,
            "completed_days_ago": 5,
            "adherence": {"prob": 0.9},
        }

        med_request = self.factory.create_medication_request(
            patient_id="patient-123",
            medication_def=med_def,
            medication_id="med-completed",
        )

        assert med_request.status == "completed"
        assert med_request.id == "med-completed"
        assert med_request.dispenseRequest.validityPeriod.end is not None
        assert med_request.note[0].text.startswith("Estimated adherence probability")
        bounds_end = med_request.dosageInstruction[0].timing["repeat"]["boundsPeriod"]["end"]
        validity_end = med_request.dispenseRequest.validityPeriod.end
        if hasattr(bounds_end, "isoformat"):
            bounds_end = bounds_end.isoformat()
        if hasattr(validity_end, "isoformat"):
            validity_end = validity_end.isoformat()
        assert bounds_end == validity_end

    def test_create_encounter(self):
        """Test creating an encounter resource."""
        encounter_def = {
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory"
            },
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB"
            },
            "duration_hours": 2
        }

        encounter = self.factory.create_encounter(
            patient_id="patient-123",
            encounter_def=encounter_def,
            encounter_id="enc-789"
        )

        assert isinstance(encounter, Encounter)
        assert encounter.id == "enc-789"
        assert encounter.status == "finished"
        assert encounter.class_fhir.code == "AMB"
        assert encounter.type[0].coding[0].code == "AMB"
        assert encounter.subject.reference == "Patient/patient-123"
        assert encounter.period is not None
        assert encounter.period.start is not None
        assert encounter.period.end is not None

        # Check duration is approximately 2 hours
        start = datetime.fromisoformat(encounter.period.start.replace('+00:00', ''))
        end = datetime.fromisoformat(encounter.period.end.replace('+00:00', ''))
        duration_hours = (end - start).total_seconds() / 3600
        assert 1.9 <= duration_hours <= 2.1

    def test_create_encounter_default_duration(self):
        """Test encounter with default duration."""
        encounter_def = {
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "IMP",
                "display": "inpatient"
            }
        }

        encounter = self.factory.create_encounter(
            patient_id="patient-123",
            encounter_def=encounter_def
        )

        # Should have default 1 hour duration
        start = datetime.fromisoformat(encounter.period.start.replace('+00:00', ''))
        end = datetime.fromisoformat(encounter.period.end.replace('+00:00', ''))
        duration_hours = (end - start).total_seconds() / 3600
        assert 0.9 <= duration_hours <= 1.1

    def test_deterministic_generation(self):
        """Test that using same seed produces same results."""
        factory1 = ResourceFactory(SeededRandom(100))
        factory2 = ResourceFactory(SeededRandom(100))

        patient_def = {"gender": "male"}

        patient1 = factory1.create_patient(patient_def)
        patient2 = factory2.create_patient(patient_def)

        assert patient1.id == patient2.id
        assert patient1.identifier[0].value == patient2.identifier[0].value

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        factory1 = ResourceFactory(SeededRandom(100))
        factory2 = ResourceFactory(SeededRandom(200))

        patient_def = {"gender": "male"}

        patient1 = factory1.create_patient(patient_def)
        patient2 = factory2.create_patient(patient_def)

        assert patient1.id != patient2.id