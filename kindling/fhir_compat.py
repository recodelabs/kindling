"""Runtime patches that smooth over differences in ``fhir.resources`` versions.

This project was originally written against an older release of the
``fhir.resources`` package.  The bundled tests expect a few convenient
helpers – for example a ``resource_type`` attribute on every resource,
``Condition`` objects that default required statuses, and ``Timing``
instances that behave like dictionaries.  The current upstream
implementation based on Pydantic v2 no longer provides those behaviours,
which leads to a cascade of validation errors inside the test-suite.

To keep the production code simple while restoring backwards
compatibility we install a couple of targeted monkey patches when the
Kindling modules are imported.  The patches are intentionally small and
only touch the pieces that the tests rely on.
"""

from __future__ import annotations

from typing import Any, Optional


_PATCH_APPLIED = False


class _ClassFHIRList(list):
    """List subclass that exposes the first coding's attributes.

    ``Encounter.class_fhir`` used to return a single ``Coding`` instance in
    older versions of ``fhir.resources``.  The modern implementation
    follows the R5 specification and returns a list of ``CodeableConcept``
    objects instead.  The compatibility wrapper keeps the list behaviour
    while exposing ``code``/``system``/``display`` attributes so that the
    historic tests keep working.
    """

    def _first_coding(self) -> Optional[Any]:
        for concept in self:
            coding = getattr(concept, "coding", None)
            if coding:
                return coding[0]
        return None

    @property
    def code(self) -> Optional[str]:
        coding = self._first_coding()
        return getattr(coding, "code", None)

    @property
    def system(self) -> Optional[str]:
        coding = self._first_coding()
        return getattr(coding, "system", None)

    @property
    def display(self) -> Optional[str]:
        coding = self._first_coding()
        return getattr(coding, "display", None)


def _wrap_class_fhir(value: Any) -> Any:
    """Return a backwards compatible representation for ``class_fhir``."""

    if isinstance(value, list) and not isinstance(value, _ClassFHIRList):
        wrapped = _ClassFHIRList(value)
        return wrapped
    return value


def apply_fhir_compatibility() -> None:
    """Install the runtime patches exactly once."""

    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    # Import locally so that the dependency is optional until this
    # function is executed.
    from fhir.resources.condition import Condition
    from fhir.resources.encounter import Encounter
    from fhir.resources.patient import Patient
    from fhir.resources.resource import Resource as FHIRResource
    from fhir.resources.timing import Timing
    from fhir.resources.period import Period

    from .config import RESOURCE_DEFAULTS, SYSTEMS
    from fhir.resources.codeableconcept import CodeableConcept
    from fhir.resources.coding import Coding

    _PATCH_APPLIED = True

    # ------------------------------------------------------------------
    # Expose the legacy ``resource_type`` attribute on every resource.
    # ------------------------------------------------------------------
    if not isinstance(getattr(FHIRResource, "resource_type", None), property):

        def _resource_type(self: Any) -> str:
            return getattr(self, "__resource_type__", self.__class__.__name__)

        FHIRResource.resource_type = property(_resource_type)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Condition default statuses – the newer models require them while the
    # historic tests expect they are optional.  Inject the defaults during
    # initialisation before delegating to the real constructor.
    # ------------------------------------------------------------------
    original_condition_init = Condition.__init__

    def _condition_init(self: Condition, *args: Any, **kwargs: Any) -> None:
        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                data = dict(args[0])
                data.update(kwargs)
            else:
                original_condition_init(self, *args, **kwargs)
                return
        else:
            data = dict(kwargs)

        def _status(system_key: str, code_key: str) -> CodeableConcept:
            return CodeableConcept(
                coding=[
                    Coding(
                        system=SYSTEMS[system_key],
                        code=RESOURCE_DEFAULTS[code_key],
                    )
                ]
            )

        if not data.get("clinicalStatus"):
            data["clinicalStatus"] = _status(
                "HL7_CONDITION_CLINICAL", "CONDITION_CLINICAL_STATUS"
            )

        if not data.get("verificationStatus"):
            data["verificationStatus"] = _status(
                "HL7_CONDITION_VER_STATUS", "CONDITION_VERIFICATION_STATUS"
            )

        original_condition_init(self, **data)

    Condition.__init__ = _condition_init  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Timing should behave like a dictionary for backwards compatibility.
    # ------------------------------------------------------------------
    if not hasattr(Timing, "__getitem__"):

        def _timing_getitem(self: Timing, key: str) -> Any:
            return self.model_dump(mode="python")[key]

        def _timing_get(self: Timing, key: str, default: Any = None) -> Any:
            return self.model_dump(mode="python").get(key, default)

        Timing.__getitem__ = _timing_getitem  # type: ignore[assignment]
        Timing.get = _timing_get  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Encounter exposes ``period`` and a list that looks like the legacy
    # ``class_fhir`` structure.
    # ------------------------------------------------------------------
    if not isinstance(getattr(Encounter, "period", None), property):

        def _get_period(self: Encounter) -> Any:
            return getattr(self, "actualPeriod", None)

        def _set_period(self: Encounter, value: Any) -> None:
            setattr(self, "actualPeriod", value)

        Encounter.period = property(_get_period, _set_period)  # type: ignore[attr-defined]

    if not hasattr(Encounter, "__kindling_original_getattribute__"):
        Encounter.__kindling_original_getattribute__ = Encounter.__getattribute__  # type: ignore[attr-defined]

        def _encounter_getattribute(self: Encounter, item: str) -> Any:  # type: ignore[override]
            original = Encounter.__kindling_original_getattribute__  # type: ignore[attr-defined]
            value = original(self, item)
            if item == "class_fhir":
                wrapped = _wrap_class_fhir(value)
                if wrapped is not value:
                    self.__dict__["class_fhir"] = wrapped
                    return wrapped
            return value

        Encounter.__getattribute__ = _encounter_getattribute  # type: ignore[assignment]

    if not hasattr(Patient, "__kindling_original_getattribute__"):
        Patient.__kindling_original_getattribute__ = Patient.__getattribute__  # type: ignore[attr-defined]

        def _patient_getattribute(self: Patient, item: str) -> Any:  # type: ignore[override]
            original = Patient.__kindling_original_getattribute__  # type: ignore[attr-defined]
            value = original(self, item)
            if item == "birthDate" and value is not None and not isinstance(value, str):
                if hasattr(value, "isoformat"):
                    string_value = value.isoformat()
                    self.__dict__["birthDate"] = string_value
                    return string_value
            return value

        Patient.__getattribute__ = _patient_getattribute  # type: ignore[assignment]

    if not hasattr(Period, "__kindling_original_getattribute__"):
        Period.__kindling_original_getattribute__ = Period.__getattribute__  # type: ignore[attr-defined]

        def _period_getattribute(self: Period, item: str) -> Any:  # type: ignore[override]
            original = Period.__kindling_original_getattribute__  # type: ignore[attr-defined]
            value = original(self, item)
            if item in {"start", "end"} and value is not None and not isinstance(value, str):
                if hasattr(value, "isoformat"):
                    string_value = value.isoformat()
                    self.__dict__[item] = string_value
                    return string_value
            return value

        Period.__getattribute__ = _period_getattribute  # type: ignore[assignment]


__all__ = ["apply_fhir_compatibility"]

