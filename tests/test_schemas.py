"""Tests for Pydantic input validation schemas."""

import pytest
from pydantic import ValidationError

from kindling.schemas import (
    AdherenceDef,
    CodingDef,
    ConditionDef,
    CoverageDef,
    DemographicsConfig,
    DiagnosticReportDef,
    EncounterDef,
    ImmunizationDef,
    MedicationDef,
    NameDef,
    ObservationDef,
    OutputConfig,
    PatientDef,
    PersonaSchema,
    ProfileSchema,
    RelatedPersonDef,
    ResourcesConfig,
    Rule,
    TimesConfig,
    ValueRange,
    format_validation_error,
)


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------


class TestCodingDef:
    def test_basic(self):
        c = CodingDef(system="http://snomed.info/sct", code="44054006", display="Diabetes")
        assert c.code == "44054006"

    def test_value_field_accepted(self):
        c = CodingDef(**{"system": "http://snomed.info/sct", "value": "44054006", "display": "Diabetes"})
        assert c.value == "44054006"

    def test_both_code_and_value_accepted(self):
        c = CodingDef(**{"system": "x", "code": "A", "value": "B"})
        assert c.code == "A"
        assert c.value == "B"

    def test_empty(self):
        c = CodingDef()
        assert c.code is None


class TestValueRange:
    def test_valid(self):
        r = ValueRange(min=1.0, max=5.0)
        assert r.min == 1.0
        assert r.max == 5.0

    def test_equal_bounds(self):
        r = ValueRange(min=3.0, max=3.0)
        assert r.min == r.max

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError, match="min.*must be <= max"):
            ValueRange(min=10, max=5)


class TestAdherenceDef:
    def test_valid(self):
        a = AdherenceDef(prob=0.85)
        assert a.prob == 0.85

    def test_out_of_range_high(self):
        with pytest.raises(ValidationError):
            AdherenceDef(prob=1.5)

    def test_out_of_range_low(self):
        with pytest.raises(ValidationError):
            AdherenceDef(prob=-0.1)


class TestTimesConfig:
    def test_valid(self):
        t = TimesConfig(qty=4, lookback_months=12)
        assert t.qty == 4

    def test_qty_zero_rejected(self):
        with pytest.raises(ValidationError):
            TimesConfig(qty=0)


# ---------------------------------------------------------------------------
# Resource definition models
# ---------------------------------------------------------------------------


class TestConditionDef:
    def test_valid(self):
        c = ConditionDef(
            code={"system": "http://snomed.info/sct", "value": "44054006", "display": "Diabetes"},
            onset={"years_ago": 5},
        )
        assert c.code.value == "44054006"
        assert c.onset.years_ago == 5

    def test_code_required(self):
        with pytest.raises(ValidationError):
            ConditionDef()


class TestObservationDef:
    def test_with_range(self):
        o = ObservationDef(loinc="4548-4", display="HbA1c", range={"min": 7.0, "max": 8.5}, unit="%")
        assert o.range.min == 7.0

    def test_invalid_range_rejected(self):
        with pytest.raises(ValidationError, match="min.*must be <= max"):
            ObservationDef(loinc="x", range={"min": 100, "max": 1})


class TestEncounterDef:
    def test_class_alias(self):
        e = EncounterDef(**{"class": "AMB", "qty": 2})
        assert e.encounter_class == "AMB"
        assert e.qty == 2

    def test_class_as_dict(self):
        e = EncounterDef(**{"class": {"system": "x", "code": "AMB"}})
        assert e.encounter_class == {"system": "x", "code": "AMB"}

    def test_qty_zero_rejected(self):
        with pytest.raises(ValidationError):
            EncounterDef(qty=0)

    def test_serialises_class_key(self):
        e = EncounterDef(**{"class": "AMB"})
        d = e.model_dump(by_alias=True)
        assert "class" in d


class TestMedicationDef:
    def test_valid(self):
        m = MedicationDef(rxnorm="860975", display="metformin", adherence={"prob": 0.85})
        assert m.adherence.prob == 0.85


class TestRelatedPersonDef:
    def test_valid(self):
        rp = RelatedPersonDef(
            relationship="child",
            name={"family": "Dlamini", "given": ["Sipho"]},
            gender="male",
        )
        assert rp.relationship == "child"


class TestImmunizationDef:
    def test_valid(self):
        i = ImmunizationDef(
            vaccine={"system": "http://hl7.org/fhir/sid/cvx", "code": "140", "display": "Influenza"},
            qty=2,
        )
        assert i.vaccine.code == "140"
        assert i.qty == 2


class TestCoverageDef:
    def test_valid(self):
        c = CoverageDef(status="active", kind="insurance", payor="Organization/default")
        assert c.status == "active"


class TestDiagnosticReportDef:
    def test_with_observations(self):
        dr = DiagnosticReportDef(
            code={"system": "http://loinc.org", "value": "24323-8", "display": "CMP"},
            status="final",
            observations=[
                {"loinc": "2345-7", "display": "Glucose", "range": {"min": 165, "max": 165}, "unit": "mg/dL"},
            ],
        )
        assert dr.code.value == "24323-8"
        assert len(dr.observations) == 1


# ---------------------------------------------------------------------------
# Structural models
# ---------------------------------------------------------------------------


class TestOutputConfig:
    def test_valid_modes(self):
        for mode in ("transaction", "collection"):
            o = OutputConfig(mode=mode)
            assert o.mode == mode

    def test_invalid_mode(self):
        with pytest.raises(ValidationError, match="output mode"):
            OutputConfig(mode="invalid")


class TestResourcesConfig:
    def test_with_rules(self):
        rc = ResourcesConfig(
            include=["Patient", "Condition"],
            rules=[
                {
                    "name": "test_rule",
                    "when": {"condition": "true"},
                    "then": {
                        "add_conditions": [
                            {"code": {"system": "x", "value": "1", "display": "d"}}
                        ]
                    },
                }
            ],
        )
        assert len(rc.rules) == 1
        assert rc.rules[0].then.add_conditions[0].code.value == "1"


# ---------------------------------------------------------------------------
# Top-level schemas
# ---------------------------------------------------------------------------


class TestProfileSchema:
    def test_valid_profile(self):
        p = ProfileSchema(
            version="0.1",
            mode="cohort",
            demographics={"age": {"min": 18, "max": 90}},
            resources={
                "rules": [
                    {
                        "name": "diabetes",
                        "when": {"condition": "age > 50"},
                        "then": {
                            "add_conditions": [
                                {
                                    "code": {
                                        "system": "http://snomed.info/sct",
                                        "value": "44054006",
                                        "display": "Type 2 diabetes mellitus",
                                    },
                                    "onset": {"years_ago": 5},
                                }
                            ]
                        },
                    }
                ]
            },
        )
        assert p.mode == "cohort"
        assert p.version == "0.1"

    def test_defaults(self):
        p = ProfileSchema()
        assert p.mode == "cohort"
        assert p.demographics == {}
        assert p.resources == {}
        assert p.output == {}
        assert p.single_patient == {}

    def test_invalid_mode(self):
        with pytest.raises(ValidationError, match="mode must be"):
            ProfileSchema(mode="invalid")


class TestPersonaSchema:
    def test_valid_persona(self):
        p = PersonaSchema(
            version="0.1",
            name="test_persona",
            description="A test persona",
            patient={"name": {"family": "Doe", "given": ["John"]}, "gender": "male"},
            resources={
                "include": ["Patient"],
                "rules": [
                    {
                        "name": "r1",
                        "when": {"condition": "true"},
                        "then": {
                            "add_conditions": [
                                {"code": {"system": "x", "value": "1", "display": "d"}}
                            ]
                        },
                    }
                ],
            },
            output={"mode": "transaction", "bundle_size": 100},
        )
        assert p.name == "test_persona"
        assert p.patient.gender == "male"
        assert p.resources.rules[0].then.add_conditions[0].code.value == "1"
        assert p.output.mode == "transaction"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            PersonaSchema(patient={"name": {"family": "X"}})

    def test_patient_required(self):
        with pytest.raises(ValidationError):
            PersonaSchema(name="x")

    def test_model_dump_preserves_class_alias(self):
        p = PersonaSchema(
            name="t",
            patient={"name": {"family": "X"}},
            resources={
                "rules": [
                    {
                        "name": "r",
                        "then": {
                            "encounters": [{"class": "AMB", "qty": 1}]
                        },
                    }
                ]
            },
        )
        d = p.model_dump(by_alias=True)
        enc = d["resources"]["rules"][0]["then"]["encounters"][0]
        assert "class" in enc


# ---------------------------------------------------------------------------
# format_validation_error
# ---------------------------------------------------------------------------


class TestFormatValidationError:
    def test_readable_output(self):
        with pytest.raises(ValidationError) as exc_info:
            ProfileSchema(mode="bad")
        msg = format_validation_error(exc_info.value)
        assert "Validation errors:" in msg
        assert "mode" in msg
