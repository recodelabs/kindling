"""Command-line interface for Kindling."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Union

import click
import yaml

from .generator import Generator
from .persona_loader import PersonaLoader
from .validator import FHIRValidator
from .utils.r4_converter import convert_bundle_to_r4


def datetime_json_encoder(obj: Any) -> str:
    """Custom JSON encoder for datetime objects to use ISO format with T separator."""
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return str(obj)


def _serialize_bundle_to_json(bundle: Any) -> str:
    """Serialize a bundle to JSON string with R4 conversion.

    Args:
        bundle: Bundle to serialize

    Returns:
        JSON string representation
    """
    bundle_data = convert_bundle_to_r4(bundle.dict())
    return json.dumps(bundle_data, indent=2, default=datetime_json_encoder)


def _write_bundle_to_file(bundle: Any, file_path: Union[str, Path]) -> None:
    """Write a bundle to a JSON file with R4 conversion.

    Args:
        bundle: Bundle to write
        file_path: Path to output file
    """
    with open(file_path, 'w') as f:
        bundle_data = convert_bundle_to_r4(bundle.dict())
        json.dump(bundle_data, f, indent=2, default=datetime_json_encoder)


def _write_bundles_array_to_file(bundles: list, file_path: Union[str, Path]) -> None:
    """Write an array of bundles to a JSON file with R4 conversion.

    Args:
        bundles: List of bundles to write
        file_path: Path to output file
    """
    with open(file_path, 'w') as f:
        bundles_data = [convert_bundle_to_r4(b.dict()) for b in bundles]
        json.dump(bundles_data, f, indent=2, default=datetime_json_encoder)


@click.command()
@click.option(
    "--profile",
    type=click.Path(exists=True),
    help="Path to profile YAML/JSON file"
)
@click.option(
    "--persona",
    type=str,
    help="Name of built-in persona to use"
)
@click.option(
    "--count",
    type=int,
    default=1,
    help="Number of patients to generate (for cohort mode)"
)
@click.option(
    "--bundle-type",
    type=click.Choice(["transaction", "collection"]),
    default="transaction",
    help="Type of bundle to generate"
)
@click.option(
    "--bundle-size",
    type=int,
    default=100,
    help="Maximum resources per bundle"
)
@click.option(
    "--seed",
    type=int,
    help="Random seed for deterministic generation"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (default: stdout)"
)
@click.option(
    "--list-personas",
    is_flag=True,
    help="List available personas and exit"
)
@click.option(
    "--server",
    type=str,
    help="FHIR server URL for upload"
)
@click.option(
    "--validate",
    is_flag=True,
    help="Validate resources before output/upload"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform dry run without upload"
)
@click.option(
    "--resources",
    type=str,
    help="Comma-separated list of resources to include (e.g., Patient,Condition,Observation)"
)
@click.option(
    "--request-method",
    type=click.Choice(["POST", "PUT", "CONDITIONAL"]),
    default="POST",
    help="HTTP method for transaction bundles (POST=server assigns ID, PUT=upsert with ID, CONDITIONAL=match by identifier)"
)
def main(
    profile: Optional[str],
    persona: Optional[str],
    count: int,
    bundle_type: str,
    bundle_size: int,
    seed: Optional[int],
    output: Optional[str],
    list_personas: bool,
    server: Optional[str],
    validate: bool,
    dry_run: bool,
    resources: Optional[str],
    request_method: str
):
    """Kindling - Lightweight FHIR synthetic data generator.

    Generate synthetic FHIR data from profiles or built-in personas.
    """
    # List personas if requested
    if list_personas:
        loader = PersonaLoader()
        personas = loader.list_personas()
        if personas:
            click.echo("Available personas:")
            for p in personas:
                click.echo(f"  - {p}")
        else:
            click.echo("No personas found.")
        sys.exit(0)

    # Validate inputs
    if not profile and not persona:
        click.echo("Error: Must specify either --profile or --persona", err=True)
        sys.exit(1)

    if profile and persona:
        click.echo("Error: Cannot specify both --profile and --persona", err=True)
        sys.exit(1)

    # Parse resource filter if provided
    resource_filter = None
    if resources:
        resource_filter = [r.strip() for r in resources.split(',')]
        click.echo(f"Limiting to resources: {', '.join(resource_filter)}", err=True)

    # Create generator
    try:
        if profile:
            click.echo(f"Loading profile: {profile}", err=True)
            generator = Generator.from_profile(profile, seed=seed)
        else:
            click.echo(f"Loading persona: {persona}", err=True)
            generator = Generator.from_persona(persona, seed=seed)
    except FileNotFoundError as e:
        click.echo(f"Error: File not found - {e}", err=True)
        sys.exit(1)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML format - {e}", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON format - {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid configuration - {e}", err=True)
        sys.exit(1)

    # Apply resource filter if provided
    if resource_filter:
        generator.set_resource_filter(resource_filter)

    # Generate data
    try:
        click.echo(f"Generating {count} patient(s)...", err=True)
        if request_method == "PUT":
            click.echo(f"Using PUT method - upsert with generated IDs", err=True)
        elif request_method == "CONDITIONAL":
            click.echo(f"Using conditional create - match by identifier", err=True)
        result = generator.generate(
            count=count,
            bundle_type=bundle_type,
            bundle_size=bundle_size,
            request_method=request_method
        )
    except ValueError as e:
        click.echo(f"Error: Invalid generation parameters - {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"Error: Generation failed - {e}", err=True)
        sys.exit(1)

    # Handle validation
    if validate:
        click.echo("Validating resources...", err=True)
        validator = FHIRValidator()

        if isinstance(result, list):
            for i, bundle in enumerate(result):
                validation_result = validator.validate_bundle(bundle)
                if not validation_result.is_valid:
                    click.echo(f"Bundle {i} validation failed:", err=True)
                    click.echo(str(validation_result), err=True)
                    sys.exit(1)
        else:
            validation_result = validator.validate_bundle(result)
            if not validation_result.is_valid:
                click.echo("Bundle validation failed:", err=True)
                click.echo(str(validation_result), err=True)
                sys.exit(1)

        click.echo("✓ Validation complete - all bundles valid", err=True)

    # Handle server upload
    if server:
        click.echo("Error: Server upload functionality is not yet implemented", err=True)
        click.echo("Please save to a file using --output and upload manually", err=True)
        sys.exit(1)

    # Output results
    try:
        if isinstance(result, list):
            # Multiple bundles
            if output:
                output_path = Path(output)
                if output_path.suffix == ".json":
                    # Single file with array
                    _write_bundles_array_to_file(result, output_path)
                    click.echo(f"Wrote {len(result)} bundles to {output_path}", err=True)
                else:
                    # Directory with multiple files
                    output_path.mkdir(parents=True, exist_ok=True)
                    for i, bundle in enumerate(result):
                        bundle_file = output_path / f"bundle_{i:04d}.json"
                        _write_bundle_to_file(bundle, bundle_file)
                    click.echo(f"Wrote {len(result)} bundles to {output_path}/", err=True)
            else:
                # Output to stdout
                for bundle in result:
                    click.echo(_serialize_bundle_to_json(bundle))
        else:
            # Single bundle
            if output:
                _write_bundle_to_file(result, output)
                click.echo(f"Wrote bundle to {output}", err=True)
            else:
                click.echo(_serialize_bundle_to_json(result))

        click.echo("Generation complete!", err=True)

    except IOError as e:
        click.echo(f"Error: Failed to write output - {e}", err=True)
        sys.exit(1)
    except OSError as e:
        click.echo(f"Error: File system error - {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()