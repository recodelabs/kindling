"""Pydantic v2 input validation schemas for Kindling profiles and personas."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helper: format ValidationError for end users
# ---------------------------------------------------------------------------

def format_validation_error(exc) -> str:
    """Format a Pydantic ValidationError into a readable message.

    Args:
        exc: A pydantic.ValidationError instance.

    Returns:
        A human-friendly multi-line string.
    """
    lines = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err["loc"]) if err["loc"] else "(root)"
        lines.append(f"  {loc}: {err['msg']}")
    return "Validation errors:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Leaf / shared models
# ---------------------------------------------------------------------------

class CodingDef(BaseModel):
    """A code triple (system / code|value / display).

    Profiles use ``value`` while some contexts use ``code``.  Both are
    accepted and preserved so downstream code (which reads ``value``)
    continues to work unchanged.
    """

    model_config = ConfigDict(extra="allow")

    system: Optional[str] = None
    code: Optional[str] = None
    value: Optional[str] = None
    display: Optional[str] = None


class ValueRange(BaseModel):
    """Numeric min/max range (e.g. for observation values)."""

    min: float = 0
    max: float = 100

    @model_validator(mode="after")
    def _min_le_max(self):
        if self.min > self.max:
            raise ValueError(f"min ({self.min}) must be <= max ({self.max})")
        return self


class NameDef(BaseModel):
    """Patient / person name."""

    model_config = ConfigDict(extra="allow")

    family: Optional[str] = None
    given: Optional[List[str]] = None


class AddressDef(BaseModel):
    """Postal address."""

    model_config = ConfigDict(extra="allow")

    line: Optional[List[str]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class TelecomDef(BaseModel):
    """Contact point."""

    model_config = ConfigDict(extra="allow")

    system: Optional[str] = "phone"
    value: Optional[str] = None
    use: Optional[str] = "home"


class IdentifierDef(BaseModel):
    """FHIR Identifier."""

    model_config = ConfigDict(extra="allow")

    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None


class OnsetDef(BaseModel):
    """Condition onset — either years_ago or days_ago."""

    model_config = ConfigDict(extra="allow")

    years_ago: Optional[int] = None
    days_ago: Optional[int] = None


class TimesConfig(BaseModel):
    """How many times to repeat an observation and over what period."""

    model_config = ConfigDict(extra="allow")

    qty: int = Field(default=1, ge=1)
    lookback_months: Optional[int] = None
    days_ago: Optional[int] = None


class AdherenceDef(BaseModel):
    """Medication adherence probability."""

    prob: float = Field(default=1.0, ge=0.0, le=1.0)


class PeriodDef(BaseModel):
    """A date period (start / end), with optional relative days_ago helpers."""

    model_config = ConfigDict(extra="allow")

    start: Optional[str] = None
    end: Optional[str] = None
    start_days_ago: Optional[int] = None
    end_days_ago: Optional[int] = None


# ---------------------------------------------------------------------------
# Resource definition models
# ---------------------------------------------------------------------------

class PatientDef(BaseModel):
    """Patient resource definition (single-patient mode or persona)."""

    model_config = ConfigDict(extra="allow")

    name: Optional[NameDef] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    identifiers: Optional[List[IdentifierDef]] = None
    address: Optional[AddressDef] = None
    telecom: Optional[List[TelecomDef]] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ConditionDef(BaseModel):
    """Condition resource definition."""

    model_config = ConfigDict(extra="allow")

    code: CodingDef
    onset: Optional[OnsetDef] = None


class ObservationDef(BaseModel):
    """Observation resource definition."""

    model_config = ConfigDict(extra="allow")

    loinc: Optional[str] = None
    display: Optional[str] = None
    range: Optional[ValueRange] = None
    unit: Optional[str] = None
    value: Optional[Any] = None
    times: Optional[TimesConfig] = None
    components: Optional[List[Any]] = None
    value_type: Optional[str] = None
    positive: Optional[bool] = None
    latest_value: Optional[float] = None


class MedicationDef(BaseModel):
    """Medication (MedicationRequest) definition."""

    model_config = ConfigDict(extra="allow")

    rxnorm: Optional[str] = None
    display: Optional[str] = None
    sig: Optional[str] = None
    frequency: Optional[float] = None
    adherence: Optional[AdherenceDef] = None
    status: Optional[str] = None
    duration_days: Optional[int] = None
    completed_days_ago: Optional[int] = None


class EncounterDef(BaseModel):
    """Encounter resource definition.

    ``class`` is a Python keyword, so we accept it via the alias
    ``encounter_class`` while still reading ``class`` from input data.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Optional[Union[CodingDef, List[CodingDef]]] = None
    encounter_class: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, alias="class"
    )
    qty: Optional[int] = Field(default=None, ge=1)
    spread_months: Optional[int] = None
    days_ago: Optional[int] = None
    reason: Optional[Union[str, Dict[str, Any]]] = None
    status: Optional[str] = None
    performer: Optional[str] = None
    duration_hours: Optional[float] = None
    notes: Optional[str] = None
    class_display: Optional[str] = None
    serviceProvider: Optional[str] = None


class RelatedPersonDef(BaseModel):
    """RelatedPerson resource definition."""

    model_config = ConfigDict(extra="allow")

    relationship: Optional[Union[str, Dict[str, Any]]] = None
    name: Optional[NameDef] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    identifiers: Optional[List[IdentifierDef]] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = True


class DiagnosticReportDef(BaseModel):
    """DiagnosticReport resource definition."""

    model_config = ConfigDict(extra="allow")

    code: Optional[CodingDef] = None
    status: Optional[str] = None
    days_ago: Optional[int] = None
    conclusion: Optional[str] = None
    observations: Optional[List[ObservationDef]] = None
    category: Optional[Dict[str, Any]] = None
    performer: Optional[str] = None


class ImmunizationDef(BaseModel):
    """Immunization resource definition."""

    model_config = ConfigDict(extra="allow")

    vaccine: Optional[CodingDef] = None
    qty: Optional[int] = Field(default=None, ge=1)
    days_ago: Optional[int] = None
    spread_months: Optional[int] = None
    status: Optional[str] = None
    lotNumber: Optional[str] = None
    site: Optional[Union[str, Dict[str, Any]]] = None
    route: Optional[Union[str, Dict[str, Any]]] = None


class CoverageDef(BaseModel):
    """Coverage resource definition."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    kind: Optional[str] = None
    type: Optional[Dict[str, Any]] = None
    payor: Optional[Union[str, List[str], Dict[str, Any]]] = None
    subscriber: Optional[str] = None
    identifier: Optional[Dict[str, Any]] = None
    relationship: Optional[Union[str, Dict[str, Any]]] = None
    period: Optional[PeriodDef] = None


# ---------------------------------------------------------------------------
# Structural models (rules, demographics, resources, output)
# ---------------------------------------------------------------------------

class RuleWhen(BaseModel):
    """The ``when`` clause of a rule."""

    model_config = ConfigDict(extra="allow")

    condition: str = "true"


class RuleThen(BaseModel):
    """The ``then`` clause of a rule — lists of resources to create."""

    model_config = ConfigDict(extra="allow")

    add_conditions: Optional[List[ConditionDef]] = None
    add_observations: Optional[List[ObservationDef]] = None
    meds: Optional[List[MedicationDef]] = None
    encounters: Optional[List[EncounterDef]] = None
    related_persons: Optional[List[RelatedPersonDef]] = None
    diagnostic_reports: Optional[List[DiagnosticReportDef]] = None
    immunizations: Optional[List[ImmunizationDef]] = None
    coverage: Optional[List[CoverageDef]] = None
    allergies: Optional[List[Dict[str, Any]]] = None
    procedures: Optional[List[Dict[str, Any]]] = None


class Rule(BaseModel):
    """A generation rule (when/then)."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    when: Optional[RuleWhen] = None
    then: Optional[RuleThen] = None


class DemographicsConfig(BaseModel):
    """Demographics configuration for cohort mode."""

    model_config = ConfigDict(extra="allow")

    age: Optional[ValueRange] = None
    gender: Optional[Dict[str, Any]] = None


class ResourcesConfig(BaseModel):
    """Top-level resources section of a profile or persona."""

    model_config = ConfigDict(extra="allow")

    include: Optional[List[str]] = None
    rules: Optional[List[Rule]] = None


class OutputConfig(BaseModel):
    """Output configuration."""

    model_config = ConfigDict(extra="allow")

    mode: Optional[str] = Field(default=None)
    bundle_size: Optional[int] = None

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("transaction", "collection"):
            raise ValueError(f"output mode must be 'transaction' or 'collection', got '{v}'")
        return v


# ---------------------------------------------------------------------------
# Top-level schemas
# ---------------------------------------------------------------------------

class ProfileSchema(BaseModel):
    """Top-level schema for a Kindling profile file."""

    model_config = ConfigDict(extra="allow")

    version: str = Field(default="0.1")
    mode: str = Field(default="cohort")
    demographics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    single_patient: Optional[Dict[str, Any]] = Field(default_factory=dict)
    resources: Optional[Dict[str, Any]] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        if v not in ("cohort", "single"):
            raise ValueError(f"mode must be 'cohort' or 'single', got '{v}'")
        return v


class PersonaSchema(BaseModel):
    """Top-level schema for a Kindling persona file."""

    model_config = ConfigDict(extra="allow")

    version: str = Field(default="0.1")
    name: str
    description: Optional[str] = None
    patient: PatientDef
    resources: Optional[ResourcesConfig] = None
    output: Optional[OutputConfig] = None
