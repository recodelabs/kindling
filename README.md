# Kindling

A lightweight, profile-driven FHIR synthetic data generator built on fhir.resources.

## Features

- **Profile-driven generation**: Define patient cohorts with YAML/JSON profiles
- **Persona library**: Pre-configured demo patients (diabetes, asthma, hypertension, healthy)
- **FHIR R4 support**: Generate Patient, Encounter, Condition, Observation, MedicationRequest, and more
- **Deterministic output**: Seeded RNG for reproducible data
- **Bundle generation**: Transaction or collection bundles for batch upload
- **Comprehensive validation**: Built-in FHIR validation with detailed error reporting
- **Extensible**: Plugin architecture for new resources and generators

## Installation

```bash
pip install kindling
```

Or from source:
```bash
git clone https://github.com/yourusername/kindling.git
cd kindling
pip install -e .
```

## Quick Start

### Generate from a built-in persona

```bash
# Generate Mary with Type 2 Diabetes
kindling --persona mary_diabetes --bundle-type transaction

# Generate John with Asthma
kindling --persona john_asthma --count 1

# Generate with validation
kindling --persona mary_diabetes --validate --output mary.json
```

### Generate from a profile

```bash
# Generate 100 patients from a diabetes cohort profile
kindling --profile profiles/diabetes.yaml --count 100

# Generate and validate
kindling --profile profiles/diabetes.yaml --count 10 --validate
```

### Validate existing FHIR bundles

```bash
# Validate a FHIR bundle file
kindling-validate bundle.json

# Validate with detailed output
kindling-validate bundle.json --verbose
```

### Python SDK

```python
from kindling import Generator
from kindling.validator import FHIRValidator

# Generate from persona
gen = Generator.from_persona("mary_diabetes")
bundle = gen.generate()

# Generate from profile
gen = Generator.from_profile("profiles/diabetes.yaml")
bundles = gen.generate(count=100)

# Validate generated bundle
validator = FHIRValidator()
result = validator.validate_bundle(bundle)
if result.is_valid:
    print("✓ Bundle is valid")
else:
    print(result)
```

## Available Personas

- **mary_diabetes**: 55-year-old female with Type 2 Diabetes
- **john_asthma**: 35-year-old male with Asthma
- **linda_hypertension**: 62-year-old female with Hypertension & Hyperlipidemia
- **david_healthy**: 28-year-old healthy male athlete

## Profile Schema

```yaml
version: 0.1
mode: cohort  # or 'single' for single patient
demographics:
  age:
    min: 45
    max: 65
  gender:
    distribution:
      female: 0.6
      male: 0.4
resources:
  include: [Patient, Encounter, Condition, Observation]
  rules:
    - name: diabetes_program
      when:
        condition: "age > 45"
      then:
        add_conditions:
          - code: {system: snomed, value: "44054006"}
output:
  mode: transaction
  bundle_size: 100
```

## Validation

Kindling includes comprehensive FHIR validation to ensure all generated data is compliant with the FHIR R4 specification.

### Validation Features

- **Structural validation**: Ensures bundles have required fields and proper structure
- **Resource validation**: Validates individual resources (Patient, Condition, Observation, etc.)
- **Reference integrity**: Checks that all references between resources are valid
- **JSON compliance**: Ensures output is valid JSON that can be parsed by any FHIR system
- **fhir.resources compliance**: Uses Pydantic models for automatic field validation

### Validation Output

The validator provides three levels of feedback:
- **Errors**: Critical issues that make the bundle invalid
- **Warnings**: Important issues that should be addressed
- **Info**: Helpful information about the bundle structure

### Command Line Options

```bash
# Generate with validation
kindling --persona mary_diabetes --validate

# Validate existing file
kindling-validate path/to/bundle.json

# Verbose validation with detailed output
kindling-validate path/to/bundle.json --verbose
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run validation tests specifically
pytest tests/test_validation.py -v

# Format code
black kindling/
ruff check kindling/
```

## Testing

Kindling includes a comprehensive test suite:

- **Unit tests**: Test individual components (generator, factory, parser)
- **Integration tests**: Test persona generation and validation
- **Validation tests**: Ensure FHIR compliance and JSON validity

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kindling

# Run specific test file
pytest tests/test_validation.py -v
```

## License

Apache 2.0