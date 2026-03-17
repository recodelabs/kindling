"""Tests for encounter linking - clinical resources should reference their encounters."""

from datetime import datetime, timedelta

import pytest
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.diagnosticreport import DiagnosticReport

from kindling import Generator
from kindling.resource_factory import ResourceFactory
from kindling.utils.random_utils import SeededRandom


class TestResourceFactoryEncounterRef:
    """Test that resource factory methods accept and use encounter_ref."""

    def setup_method(self):
        self.rng = SeededRandom(42)
        self.factory = ResourceFactory(self.rng)

    def test_observation_includes_encounter_reference(self):
        """Observation should have encounter field when encounter_ref is provided."""
        obs_def = {
            "loinc": "8480-6",
            "display": "Systolic blood pressure",
            "range": {"min": 120, "max": 140},
            "unit": "mmHg",
        }

        observation = self.factory.create_observation(
            patient_id="patient-1",
            observation_def=obs_def,
            observation_id="obs-1",
            encounter_ref="Encounter/enc-1",
        )

        assert isinstance(observation, Observation)
        assert observation.encounter is not None
        assert observation.encounter.reference == "Encounter/enc-1"

    def test_observation_without_encounter_ref_has_no_encounter(self):
        """Observation should have no encounter field when encounter_ref is not provided."""
        obs_def = {
            "loinc": "8480-6",
            "display": "Systolic blood pressure",
            "range": {"min": 120, "max": 140},
            "unit": "mmHg",
        }

        observation = self.factory.create_observation(
            patient_id="patient-1",
            observation_def=obs_def,
        )

        assert observation.encounter is None

    def test_condition_includes_encounter_reference(self):
        """Condition should have encounter field when encounter_ref is provided."""
        condition_def = {
            "code": {
                "system": "http://snomed.info/sct",
                "value": "38341003",
                "display": "Hypertension",
            },
            "onset": {"years_ago": 5},
        }

        condition = self.factory.create_condition(
            patient_id="patient-1",
            condition_def=condition_def,
            condition_id="cond-1",
            encounter_ref="Encounter/enc-1",
        )

        assert isinstance(condition, Condition)
        assert condition.encounter is not None
        assert condition.encounter.reference == "Encounter/enc-1"

    def test_medication_request_includes_encounter_reference(self):
        """MedicationRequest should have encounter field when encounter_ref is provided."""
        med_def = {
            "rxnorm": "314077",
            "display": "lisinopril 20 MG Oral Tablet",
            "sig": "Take 1 tablet by mouth daily",
            "frequency": 1,
        }

        med = self.factory.create_medication_request(
            patient_id="patient-1",
            medication_def=med_def,
            medication_id="med-1",
            encounter_ref="Encounter/enc-1",
        )

        assert isinstance(med, MedicationRequest)
        assert med.encounter is not None
        assert med.encounter.reference == "Encounter/enc-1"

    def test_diagnostic_report_includes_encounter_reference(self):
        """DiagnosticReport should have encounter field when encounter_ref is provided."""
        report_def = {
            "code": {
                "system": "http://loinc.org",
                "value": "57698-3",
                "display": "Lipid panel",
            },
            "category": {
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "LAB",
                "display": "Laboratory",
            },
        }

        report = self.factory.create_diagnostic_report(
            patient_id="patient-1",
            diagnostic_report_def=report_def,
            report_id="report-1",
            encounter_ref="Encounter/enc-1",
        )

        assert isinstance(report, DiagnosticReport)
        assert report.encounter is not None
        assert report.encounter.reference == "Encounter/enc-1"


class TestGeneratorEncounterLinking:
    """Test that the generator links clinical resources to encounters."""

    def test_linda_observations_have_encounter_refs(self):
        """Observations in linda_hypertension should reference encounters."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        observations = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Observation"
        ]
        encounters = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Encounter"
        ]

        assert len(encounters) > 0, "Should have encounters"
        assert len(observations) > 0, "Should have observations"

        # All observations should have an encounter reference
        for obs in observations:
            assert obs.encounter is not None, (
                f"Observation {obs.id} ({obs.code.coding[0].display}) "
                f"should reference an encounter"
            )

    def test_linda_conditions_have_encounter_refs(self):
        """Conditions in linda_hypertension should reference encounters."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        conditions = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Condition"
        ]

        assert len(conditions) > 0
        for cond in conditions:
            assert cond.encounter is not None, (
                f"Condition {cond.id} should reference an encounter"
            )

    def test_linda_medication_requests_have_encounter_refs(self):
        """MedicationRequests in linda_hypertension should reference encounters."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        meds = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "MedicationRequest"
        ]

        assert len(meds) > 0
        for med in meds:
            assert med.encounter is not None, (
                f"MedicationRequest {med.id} should reference an encounter"
            )

    def test_linda_diagnostic_reports_have_encounter_refs(self):
        """DiagnosticReports in linda_hypertension should reference encounters."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        reports = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "DiagnosticReport"
        ]

        assert len(reports) > 0
        for report in reports:
            assert report.encounter is not None, (
                f"DiagnosticReport {report.id} should reference an encounter"
            )

    def test_encounter_refs_point_to_valid_encounters(self):
        """All encounter references should point to encounters in the bundle."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        # Collect all encounter URNs/IDs from bundle entries
        encounter_urls = set()
        for entry in bundle.entry:
            if entry.resource.resource_type == "Encounter":
                # In transaction bundles, fullUrl is the URN
                encounter_urls.add(entry.fullUrl)

        # Check all encounter references resolve
        for entry in bundle.entry:
            resource = entry.resource
            enc_ref = getattr(resource, "encounter", None)
            if enc_ref is not None:
                ref_value = enc_ref.reference
                assert ref_value in encounter_urls, (
                    f"{resource.resource_type}/{resource.id} references "
                    f"{ref_value} which is not in the bundle"
                )

    def test_observation_dates_align_with_encounters(self):
        """Observation effectiveDateTimes should fall within encounter periods."""
        gen = Generator.from_persona("linda_hypertension", seed=42)
        bundle = gen.generate()

        # Build encounter lookup by fullUrl
        encounters_by_url = {}
        for entry in bundle.entry:
            if entry.resource.resource_type == "Encounter":
                encounters_by_url[entry.fullUrl] = entry.resource

        for entry in bundle.entry:
            obs = entry.resource
            if obs.resource_type != "Observation":
                continue
            if obs.encounter is None:
                continue

            enc = encounters_by_url.get(obs.encounter.reference)
            if enc is None:
                continue

            # Get the encounter start date (just the date part for comparison)
            enc_period = getattr(enc, "actualPeriod", None) or getattr(enc, "period", None)
            if enc_period and enc_period.start and obs.effectiveDateTime:
                enc_start = enc_period.start
                obs_date = obs.effectiveDateTime

                # Both should be on the same day (within 24h)
                if isinstance(enc_start, str):
                    enc_start = datetime.fromisoformat(enc_start.replace("+00:00", ""))
                if isinstance(obs_date, str):
                    obs_date = datetime.fromisoformat(obs_date.replace("+00:00", ""))

                diff = abs((obs_date - enc_start).total_seconds())
                assert diff < 86400, (
                    f"Observation date {obs_date} should be within 24h of "
                    f"encounter date {enc_start}, diff={diff}s"
                )

    def test_profile_without_encounters_still_works(self):
        """Profiles without encounters should generate resources without encounter refs."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["No-Encounters"]},
                "gender": "female",
                "birthDate": "1990-01-01",
            },
            "resources": {
                "include": ["Patient", "Condition"],
                "rules": [
                    {
                        "name": "test_rule",
                        "when": {"condition": "true"},
                        "then": {
                            "add_conditions": [
                                {
                                    "code": {
                                        "system": "http://snomed.info/sct",
                                        "value": "38341003",
                                        "display": "Hypertension",
                                    },
                                    "onset": {"years_ago": 2},
                                }
                            ]
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        conditions = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Condition"
        ]
        assert len(conditions) > 0
        # Without encounters defined, conditions should have no encounter ref
        for cond in conditions:
            assert cond.encounter is None
