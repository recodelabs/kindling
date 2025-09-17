"""Kindling - A lightweight, profile-driven FHIR synthetic data generator."""

from .fhir_compat import apply_fhir_compatibility_patches

apply_fhir_compatibility_patches()

from .generator import Generator

__version__ = "0.1.0"
__all__ = ["Generator"]