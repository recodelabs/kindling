#!/usr/bin/env python
"""Standalone validation CLI for FHIR bundles."""

import sys
import click
from pathlib import Path

from .validator import FHIRValidator


@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed validation output')
def validate(file_path: str, verbose: bool):
    """Validate a FHIR bundle JSON file.

    FILE_PATH: Path to the JSON file to validate
    """
    validator = FHIRValidator()

    click.echo(f"Validating {file_path}...", err=True)

    result = validator.validate_file(file_path)

    if verbose or not result.is_valid:
        click.echo(str(result))
    else:
        click.echo("✓ Validation passed")

    if not result.is_valid:
        sys.exit(1)


if __name__ == "__main__":
    validate()