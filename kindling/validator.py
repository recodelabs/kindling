"""Validation module for FHIR resources and bundles."""

import json
from typing import Any, Dict, List, Optional, Tuple

from fhir.resources.bundle import Bundle
from fhir.resources.resource import Resource


class ValidationResult:
    """Result of a validation operation."""

    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add an info message."""
        self.info.append(message)

    def __str__(self):
        """String representation of validation result."""
        lines = []
        if self.is_valid:
            lines.append("✓ Validation passed")
        else:
            lines.append("✗ Validation failed")

        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.info:
            lines.append(f"Info ({len(self.info)}):")
            for info in self.info:
                lines.append(f"  - {info}")

        return "\n".join(lines)


class FHIRValidator:
    """Validator for FHIR resources and bundles."""

    def validate_bundle(self, bundle: Bundle) -> ValidationResult:
        """Validate a FHIR bundle.

        Args:
            bundle: FHIR Bundle to validate

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        # Basic bundle structure validation
        bundle_dict = bundle.model_dump()
        if bundle_dict.get('resourceType') != "Bundle":
            result.add_error(f"Invalid resourceType: {bundle_dict.get('resourceType')}")

        if not bundle.type:
            result.add_error("Bundle missing type")
        elif bundle.type not in ["transaction", "collection", "document", "message", "history", "searchset", "batch"]:
            result.add_error(f"Invalid bundle type: {bundle.type}")

        if not bundle.id:
            result.add_warning("Bundle missing id")

        if not bundle.timestamp:
            result.add_warning("Bundle missing timestamp")

        # Validate entries
        if not bundle.entry:
            result.add_warning("Bundle has no entries")
        else:
            result.add_info(f"Bundle contains {len(bundle.entry)} entries")
            self._validate_entries(bundle, result)

        return result

    def _validate_entries(self, bundle: Bundle, result: ValidationResult):
        """Validate bundle entries."""
        resource_ids = set()
        references = []

        for i, entry in enumerate(bundle.entry):
            # Validate entry structure
            if not entry.resource:
                result.add_error(f"Entry {i} missing resource")
                continue

            if not entry.fullUrl:
                result.add_warning(f"Entry {i} missing fullUrl")

            # For transaction bundles, validate request
            if bundle.type == "transaction":
                if not entry.request:
                    result.add_error(f"Entry {i} missing request (required for transaction bundle)")
                elif not entry.request.method:
                    result.add_error(f"Entry {i} missing request.method")
                elif not entry.request.url:
                    result.add_error(f"Entry {i} missing request.url")

            # Validate resource
            resource = entry.resource
            self._validate_resource(resource, result, i)

            # Collect IDs and references for integrity check
            if resource.id:
                resource_ids.add(f"{resource.__class__.__name__}/{resource.id}")

            # Collect references
            if hasattr(resource, "subject") and resource.subject and resource.subject.reference:
                references.append((i, "subject", resource.subject.reference))

        # Check referential integrity
        self._check_references(resource_ids, references, result)

    def _validate_resource(self, resource: Resource, result: ValidationResult, index: int):
        """Validate individual resource."""
        resource_type = resource.__class__.__name__

        # Basic resource validation
        if not resource.id:
            result.add_warning(f"Resource {index} ({resource_type}) missing id")

        # Resource-specific validation
        if resource_type == "Patient":
            self._validate_patient(resource, result, index)
        elif resource_type == "Condition":
            self._validate_condition(resource, result, index)
        elif resource_type == "Observation":
            self._validate_observation(resource, result, index)
        elif resource_type == "MedicationRequest":
            self._validate_medication_request(resource, result, index)
        elif resource_type == "Encounter":
            self._validate_encounter(resource, result, index)

    def _validate_patient(self, patient, result: ValidationResult, index: int):
        """Validate Patient resource."""
        if not patient.name or len(patient.name) == 0:
            result.add_error(f"Patient {index} missing name")

        if not patient.gender:
            result.add_warning(f"Patient {index} missing gender")
        elif patient.gender not in ["male", "female", "other", "unknown"]:
            result.add_error(f"Patient {index} invalid gender: {patient.gender}")

        if not patient.birthDate:
            result.add_warning(f"Patient {index} missing birthDate")

    def _validate_condition(self, condition, result: ValidationResult, index: int):
        """Validate Condition resource."""
        if not condition.code:
            result.add_error(f"Condition {index} missing code")

        if not condition.subject:
            result.add_error(f"Condition {index} missing subject")

        if not condition.clinicalStatus:
            result.add_warning(f"Condition {index} missing clinicalStatus")

        if not condition.verificationStatus:
            result.add_warning(f"Condition {index} missing verificationStatus")

    def _validate_observation(self, observation, result: ValidationResult, index: int):
        """Validate Observation resource."""
        if not observation.status:
            result.add_error(f"Observation {index} missing status")
        elif observation.status not in ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]:
            result.add_error(f"Observation {index} invalid status: {observation.status}")

        if not observation.code:
            result.add_error(f"Observation {index} missing code")

        if not observation.subject:
            result.add_error(f"Observation {index} missing subject")

    def _validate_medication_request(self, med_request, result: ValidationResult, index: int):
        """Validate MedicationRequest resource."""
        if not med_request.status:
            result.add_error(f"MedicationRequest {index} missing status")
        elif med_request.status not in ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"]:
            result.add_error(f"MedicationRequest {index} invalid status: {med_request.status}")

        if not med_request.intent:
            result.add_error(f"MedicationRequest {index} missing intent")
        elif med_request.intent not in ["proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"]:
            result.add_error(f"MedicationRequest {index} invalid intent: {med_request.intent}")

        if not med_request.medication:
            result.add_error(f"MedicationRequest {index} missing medication")

        if not med_request.subject:
            result.add_error(f"MedicationRequest {index} missing subject")

    def _validate_encounter(self, encounter, result: ValidationResult, index: int):
        """Validate Encounter resource."""
        if not encounter.status:
            result.add_error(f"Encounter {index} missing status")
        elif encounter.status not in ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"]:
            result.add_error(f"Encounter {index} invalid status: {encounter.status}")

        if not encounter.class_fhir:
            result.add_error(f"Encounter {index} missing class")

        if not encounter.subject:
            result.add_error(f"Encounter {index} missing subject")

    def _check_references(self, resource_ids: set, references: List[Tuple[int, str, str]], result: ValidationResult):
        """Check referential integrity."""
        for index, field, reference in references:
            if not reference.startswith("urn:uuid:") and reference not in resource_ids:
                result.add_warning(f"Resource {index} has {field} reference to non-existent resource: {reference}")

    def validate_json(self, json_str: str) -> ValidationResult:
        """Validate JSON string as FHIR Bundle.

        Args:
            json_str: JSON string to validate

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        # First check if it's valid JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON: {e}")
            return result

        # Try to parse as FHIR Bundle
        try:
            bundle = Bundle.model_validate(data)
        except Exception as e:
            result.add_error(f"Invalid FHIR Bundle: {e}")
            return result

        # Validate the bundle
        return self.validate_bundle(bundle)

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate FHIR Bundle from file.

        Args:
            file_path: Path to JSON file

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        try:
            with open(file_path, 'r') as f:
                json_str = f.read()
        except Exception as e:
            result.add_error(f"Failed to read file: {e}")
            return result

        return self.validate_json(json_str)