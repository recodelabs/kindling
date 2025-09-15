"""Utilities for converting resources to R4 format."""

from typing import Any, Dict


def convert_to_r4(resource_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a resource dictionary to R4 format.

    Args:
        resource_dict: Resource dictionary in R5/R4B format

    Returns:
        Resource dictionary in R4 format
    """
    # Handle MedicationRequest conversion
    if resource_dict.get("resourceType") == "MedicationRequest":
        # Convert medication.concept to medicationCodeableConcept
        if "medication" in resource_dict:
            medication = resource_dict["medication"]
            if isinstance(medication, dict) and "concept" in medication:
                # R5 format: medication.concept -> R4: medicationCodeableConcept
                resource_dict["medicationCodeableConcept"] = medication["concept"]
                del resource_dict["medication"]

    return resource_dict


def convert_bundle_to_r4(bundle_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a bundle dictionary to R4 format.

    Args:
        bundle_dict: Bundle dictionary in R5/R4B format

    Returns:
        Bundle dictionary in R4 format
    """
    # Process each entry in the bundle
    if "entry" in bundle_dict and bundle_dict["entry"]:
        for entry in bundle_dict["entry"]:
            if "resource" in entry:
                entry["resource"] = convert_to_r4(entry["resource"])

    return bundle_dict