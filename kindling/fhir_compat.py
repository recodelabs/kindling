"""Compatibility helpers for fhir.resources v7.x.

This module patches selected classes from ``fhir.resources`` so that they
behave more like the 6.x (FHIR R4) release that Kindling was originally built
against.  The upstream project moved to FHIR R5 in v7 which introduced a few
breaking API changes (required fields, renamed attributes, richer return
types).  Our test-suite – and, more importantly, the CLI behaviour relied on by
users – still expects the older ergonomics.  Rather than pin the dependency to
an outdated version we patch the handful of places where the public behaviour
changed in incompatible ways.

The patches applied here are intentionally conservative and only touch
behaviour exercised in the tests.  They can be removed once the rest of the
codebase (and downstream callers) have been migrated to the new APIs.
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict

from fhir.resources.bundle import Bundle
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.patient import Patient
from fhir.resources.resource import Resource
from fhir.resources.timing import Timing

from .config import RESOURCE_DEFAULTS, SYSTEMS

_PATCHED = False


def apply_fhir_compatibility_patches() -> None:
    """Apply patches that restore backwards compatibility.

    The function is idempotent and safe to call multiple times; subsequent
    invocations are no-ops.  Patching happens lazily so that the additional
    imports only occur when Kindling itself is imported.
    """

    global _PATCHED
    if _PATCHED:
        return

    _patch_resource_type_property()
    _patch_condition_defaults()
    _patch_patient_birthdate_accessor()
    _patch_encounter_accessors()
    _patch_timing_mapping()
    _patch_bundle_timestamp_accessor()

    _PATCHED = True


def _patch_resource_type_property() -> None:
    """Expose ``resource_type`` on every FHIR resource instance."""

    if hasattr(Resource, "resource_type"):
        return

    @property
    def resource_type(self: Resource) -> str:  # type: ignore[misc]
        return self.__class__.__name__

    Resource.resource_type = resource_type  # type: ignore[attr-defined]


def _patch_condition_defaults() -> None:
    """Provide default clinical/verification statuses for Condition."""

    if getattr(Condition, "_kindling_condition_patched", False):
        return

    original_init = Condition.__init__

    def _patched_init(self: Condition, *args: Any, **kwargs: Any) -> None:
        if args:
            if len(args) != 1 or not isinstance(args[0], Dict):
                original_init(self, *args, **kwargs)
                return
            data = dict(args[0])
            data.update(kwargs)
        else:
            data = dict(kwargs)

        data.setdefault(
            "clinicalStatus",
            CodeableConcept(
                coding=[
                    Coding(
                        system=SYSTEMS["HL7_CONDITION_CLINICAL"],
                        code=RESOURCE_DEFAULTS["CONDITION_CLINICAL_STATUS"],
                    )
                ]
            ),
        )
        data.setdefault(
            "verificationStatus",
            CodeableConcept(
                coding=[
                    Coding(
                        system=SYSTEMS["HL7_CONDITION_VER_STATUS"],
                        code=RESOURCE_DEFAULTS["CONDITION_VERIFICATION_STATUS"],
                    )
                ]
            ),
        )

        original_init(self, **data)

    Condition.__init__ = _patched_init  # type: ignore[assignment]
    Condition._kindling_condition_patched = True  # type: ignore[attr-defined]


def _patch_patient_birthdate_accessor() -> None:
    """Ensure ``Patient.birthDate`` continues to return an ISO date string."""

    if getattr(Patient, "_kindling_birthdate_patch", False):
        return

    original_getattribute = Patient.__getattribute__

    def _patched_getattribute(self: Patient, name: str) -> Any:
        value = original_getattribute(self, name)
        if name == "birthDate" and isinstance(value, date):
            return value.isoformat()
        return value

    Patient.__getattribute__ = _patched_getattribute  # type: ignore[assignment]
    Patient._kindling_birthdate_patch = True  # type: ignore[attr-defined]


def _patch_encounter_accessors() -> None:
    """Patch Encounter to expose historical attribute names."""

    if getattr(Encounter, "_kindling_encounter_patch", False):
        return

    original_getattribute = Encounter.__getattribute__
    original_setattr = Encounter.__setattr__

    def _patched_getattribute(self: Encounter, name: str) -> Any:
        if name == "period":
            try:
                period = original_getattribute(self, "actualPeriod")
            except AttributeError:
                return None

            if period is None:
                return None

            data = period.model_dump()
            if "start" in data and isinstance(data["start"], datetime):
                data["start"] = data["start"].isoformat()
            if "end" in data and isinstance(data["end"], datetime):
                data["end"] = data["end"].isoformat()

            return SimpleNamespace(**data)

        value = original_getattribute(self, name)
        if name == "class_fhir" and isinstance(value, list) and value:
            concept = value[0]
            coding = getattr(concept, "coding", None)
            if coding:
                return coding[0]
        return value

    def _patched_setattr(self: Encounter, name: str, value: Any) -> None:
        if name == "period":
            original_setattr(self, "actualPeriod", value)
        else:
            original_setattr(self, name, value)

    Encounter.__getattribute__ = _patched_getattribute  # type: ignore[assignment]
    Encounter.__setattr__ = _patched_setattr  # type: ignore[assignment]
    Encounter._kindling_encounter_patch = True  # type: ignore[attr-defined]


def _patch_timing_mapping() -> None:
    """Expose Mapping-like access on Timing instances."""

    if hasattr(Timing, "__getitem__"):
        return

    def _timing_getitem(self: Timing, key: str) -> Any:
        data = self.model_dump()
        return data[key]

    Timing.__getitem__ = _timing_getitem  # type: ignore[assignment]


def _patch_bundle_timestamp_accessor() -> None:
    """Return ISO formatted strings for bundle timestamps."""

    if getattr(Bundle, "_kindling_timestamp_patch", False):
        return

    original_getattribute = Bundle.__getattribute__

    def _patched_getattribute(self: Bundle, name: str) -> Any:
        value = original_getattribute(self, name)
        if name == "timestamp" and isinstance(value, datetime):
            return value.isoformat()
        return value

    Bundle.__getattribute__ = _patched_getattribute  # type: ignore[assignment]
    Bundle._kindling_timestamp_patch = True  # type: ignore[attr-defined]

