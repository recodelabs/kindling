"""Tests for observation times expansion and trending values."""

from datetime import datetime, timedelta

import pytest
from fhir.resources.observation import Observation

from kindling import Generator
from kindling.resource_factory import ResourceFactory
from kindling.utils.random_utils import SeededRandom


class TestComponentFixedValue:
    """Test that observation components support fixed 'value' (not just range)."""

    def setup_method(self):
        self.rng = SeededRandom(42)
        self.factory = ResourceFactory(self.rng)

    def test_component_with_fixed_value(self):
        """Components should accept a fixed 'value' instead of 'range'."""
        obs_def = {
            "loinc": "85354-9",
            "display": "Blood pressure panel",
            "components": [
                {
                    "loinc": "8480-6",
                    "display": "Systolic blood pressure",
                    "value": 135,
                    "unit": "mmHg",
                },
                {
                    "loinc": "8462-4",
                    "display": "Diastolic blood pressure",
                    "value": 85,
                    "unit": "mmHg",
                },
            ],
        }

        obs = self.factory.create_observation(
            patient_id="p-1",
            observation_def=obs_def,
            observation_id="obs-1",
        )

        assert obs.component[0].valueQuantity.value == 135
        assert obs.component[1].valueQuantity.value == 85


class TestTimesExpansion:
    """Test that the generator expands times.qty into multiple observations."""

    def test_times_generates_multiple_observations(self):
        """A single obs_def with times.qty=4 should produce 4 observations."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["Times"]},
                "gender": "female",
                "birthDate": "1970-01-01",
            },
            "resources": {
                "include": ["Patient", "Observation", "Encounter"],
                "rules": [
                    {
                        "name": "vitals",
                        "when": {"condition": "true"},
                        "then": {
                            "encounters": [
                                {
                                    "type": {
                                        "system": "http://snomed.info/sct",
                                        "code": "390848009",
                                        "display": "Follow-up",
                                    },
                                    "class": "AMB",
                                    "qty": 4,
                                    "spread_months": 12,
                                }
                            ],
                            "add_observations": [
                                {
                                    "loinc": "39156-5",
                                    "display": "BMI",
                                    "range": {"min": 28, "max": 30},
                                    "unit": "kg/m2",
                                    "times": {"qty": 4, "lookback_months": 12},
                                }
                            ],
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        observations = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Observation"
        ]

        assert len(observations) == 4, (
            f"Expected 4 observations from times.qty=4, got {len(observations)}"
        )

    def test_times_observations_each_linked_to_encounter(self):
        """Each expanded observation should be linked to an encounter."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["Times"]},
                "gender": "female",
                "birthDate": "1970-01-01",
            },
            "resources": {
                "include": ["Patient", "Observation", "Encounter"],
                "rules": [
                    {
                        "name": "vitals",
                        "when": {"condition": "true"},
                        "then": {
                            "encounters": [
                                {
                                    "type": {
                                        "system": "http://snomed.info/sct",
                                        "code": "390848009",
                                        "display": "Follow-up",
                                    },
                                    "class": "AMB",
                                    "qty": 4,
                                    "spread_months": 12,
                                }
                            ],
                            "add_observations": [
                                {
                                    "loinc": "8867-4",
                                    "display": "Heart rate",
                                    "range": {"min": 60, "max": 80},
                                    "unit": "/min",
                                    "times": {"qty": 4, "lookback_months": 12},
                                }
                            ],
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        observations = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Observation"
        ]

        for obs in observations:
            assert obs.encounter is not None, (
                f"Observation {obs.id} should have encounter ref"
            )


class TestTrendingValues:
    """Test that trending observations interpolate values over time."""

    def test_simple_value_trend(self):
        """Observations with trend should interpolate from start to end."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["Trend"]},
                "gender": "female",
                "birthDate": "1970-01-01",
            },
            "resources": {
                "include": ["Patient", "Observation", "Encounter"],
                "rules": [
                    {
                        "name": "weight_loss",
                        "when": {"condition": "true"},
                        "then": {
                            "encounters": [
                                {
                                    "type": {
                                        "system": "http://snomed.info/sct",
                                        "code": "390848009",
                                        "display": "Follow-up",
                                    },
                                    "class": "AMB",
                                    "qty": 4,
                                    "spread_months": 12,
                                }
                            ],
                            "add_observations": [
                                {
                                    "loinc": "29463-7",
                                    "display": "Body weight",
                                    "trend": {"start": 200, "end": 185},
                                    "unit": "lbs",
                                    "times": {"qty": 4, "lookback_months": 12},
                                }
                            ],
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        observations = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Observation"
        ]

        assert len(observations) == 4

        # Extract values sorted by date (oldest first)
        dated_values = []
        for obs in observations:
            dt = obs.effectiveDateTime
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace("+00:00", ""))
            dated_values.append((dt, obs.valueQuantity.value))

        dated_values.sort(key=lambda x: x[0])
        values = [v for _, v in dated_values]

        # Oldest should be near 200, newest near 185
        assert values[0] == pytest.approx(200, abs=1)
        assert values[-1] == pytest.approx(185, abs=1)

        # Values should be decreasing
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], (
                f"Values should decrease over time: {values}"
            )

    def test_component_trend(self):
        """BP panel with trending components should show decreasing values."""
        profile = {
            "version": "0.1",
            "mode": "single",
            "single_patient": {
                "name": {"family": "Test", "given": ["BPTrend"]},
                "gender": "female",
                "birthDate": "1962-11-08",
            },
            "resources": {
                "include": ["Patient", "Observation", "Encounter"],
                "rules": [
                    {
                        "name": "bp_trend",
                        "when": {"condition": "true"},
                        "then": {
                            "encounters": [
                                {
                                    "type": {
                                        "system": "http://snomed.info/sct",
                                        "code": "390848009",
                                        "display": "Follow-up",
                                    },
                                    "class": "AMB",
                                    "qty": 4,
                                    "spread_months": 12,
                                }
                            ],
                            "add_observations": [
                                {
                                    "loinc": "85354-9",
                                    "display": "Blood pressure panel",
                                    "components": [
                                        {
                                            "loinc": "8480-6",
                                            "display": "Systolic BP",
                                            "trend": {
                                                "start": 158,
                                                "end": 125,
                                            },
                                            "unit": "mmHg",
                                        },
                                        {
                                            "loinc": "8462-4",
                                            "display": "Diastolic BP",
                                            "trend": {
                                                "start": 96,
                                                "end": 78,
                                            },
                                            "unit": "mmHg",
                                        },
                                    ],
                                    "times": {
                                        "qty": 4,
                                        "lookback_months": 12,
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        }

        gen = Generator(profile=profile, seed=42)
        bundle = gen.generate()

        observations = [
            e.resource
            for e in bundle.entry
            if e.resource.resource_type == "Observation"
        ]

        assert len(observations) == 4

        # Extract systolic values sorted by date (oldest first)
        dated_systolics = []
        for obs in observations:
            dt = obs.effectiveDateTime
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace("+00:00", ""))
            systolic = obs.component[0].valueQuantity.value
            dated_systolics.append((dt, systolic))

        dated_systolics.sort(key=lambda x: x[0])
        systolics = [v for _, v in dated_systolics]

        # Oldest should be near 158, newest near 125
        assert systolics[0] == pytest.approx(158, abs=1)
        assert systolics[-1] == pytest.approx(125, abs=1)

        # Should be decreasing
        for i in range(len(systolics) - 1):
            assert systolics[i] >= systolics[i + 1], (
                f"Systolic should decrease: {systolics}"
            )
