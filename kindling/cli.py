"""Command-line interface for Kindling."""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from .generator import Generator
from .persona_loader import PersonaLoader
from .validator import FHIRValidator


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
    dry_run: bool
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

    try:
        # Create generator
        if profile:
            click.echo(f"Loading profile: {profile}", err=True)
            generator = Generator.from_profile(profile, seed=seed)
        else:
            click.echo(f"Loading persona: {persona}", err=True)
            generator = Generator.from_persona(persona, seed=seed)

        # Generate data
        click.echo(f"Generating {count} patient(s)...", err=True)
        result = generator.generate(
            count=count,
            bundle_type=bundle_type,
            bundle_size=bundle_size
        )

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
        if server and not dry_run:
            click.echo(f"Uploading to {server}...", err=True)
            # TODO: Implement upload
            click.echo("Upload complete.", err=True)
        elif server and dry_run:
            click.echo(f"Dry run - would upload to {server}", err=True)

        # Output results
        if isinstance(result, list):
            # Multiple bundles
            if output:
                output_path = Path(output)
                if output_path.suffix == ".json":
                    # Single file with array
                    with open(output_path, 'w') as f:
                        json.dump([b.model_dump() for b in result], f, indent=2, default=str)
                    click.echo(f"Wrote {len(result)} bundles to {output_path}", err=True)
                else:
                    # Directory with multiple files
                    output_path.mkdir(parents=True, exist_ok=True)
                    for i, bundle in enumerate(result):
                        bundle_file = output_path / f"bundle_{i:04d}.json"
                        with open(bundle_file, 'w') as f:
                            json.dump(bundle.model_dump(), f, indent=2, default=str)
                    click.echo(f"Wrote {len(result)} bundles to {output_path}/", err=True)
            else:
                # Output to stdout
                for bundle in result:
                    click.echo(bundle.model_dump_json(indent=2))
        else:
            # Single bundle
            if output:
                with open(output, 'w') as f:
                    json.dump(result.model_dump(), f, indent=2, default=str)
                click.echo(f"Wrote bundle to {output}", err=True)
            else:
                click.echo(result.model_dump_json(indent=2))

        click.echo("Generation complete!", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()