---
name: kindling
description: Generate FHIR R4 synthetic healthcare data using Kindling. Use when generating test patients, creating FHIR bundles, making synthetic healthcare data, or working with personas.
argument-hint: "[persona name or description of patient]"
allowed-tools: Bash(uv run kindling*), Bash(uv run kindling-validate*), Write, Read, Glob, Grep
---

# Kindling - FHIR R4 Synthetic Data Generator

Generate realistic, deterministic FHIR R4 bundles from profiles and personas.

## Setup

Use `uv run` to run kindling (no venv activation needed):
```bash
uv run kindling [OPTIONS]
```

## Available Personas

- david_healthy
- grace_tb
- john_asthma
- linda_hypertension
- mary_diabetes
- nomsa_diabetes_malaria

List personas programmatically:
```bash
uv run kindling --list-personas
```

## CLI Reference

```
kindling --persona NAME --output FILE.json    # Generate from built-in persona
kindling --profile PATH --output FILE.json    # Generate from custom profile YAML
kindling --count N --persona NAME             # Generate cohort of N patients
kindling --seed 42 --persona NAME             # Deterministic generation
kindling --validate --persona NAME            # Validate resources during generation
kindling --bundle-type collection             # Collection bundle (default: transaction)
kindling --resources Patient,Condition        # Only include specific resource types
kindling-validate FILE.json                   # Validate a generated bundle
```

## Creating Custom Profiles

When the user wants data for a patient scenario not covered by existing personas, create a custom profile YAML.

### Profile Structure

```yaml
version: "0.1"
name: custom_profile
description: "Description of the patient"

patient:
  identifiers:
    - system: "http://hospital.example/mrn"
      value: "MRN-001"
  name:
    family: "LastName"
    given: ["FirstName"]
  gender: male|female
  birthDate: "YYYY-MM-DD"
  address:
    line: ["123 Main St"]
    city: "City"
    state: "ST"
    postalCode: "12345"
    country: "US"

resources:
  include:
    - Patient
    - Condition
    - Observation
    - MedicationRequest
    - Encounter
    - Procedure
    - Coverage
    - Practitioner
    - Organization

  rules:
    - name: rule_name
      when:
        condition: "true"
      then:
        add_conditions:
          - code:
              system: "http://snomed.info/sct"
              value: "SNOMED_CODE"
              display: "Condition name"
            onset:
              years_ago: N

        add_observations:
          # Simple observation
          - loinc: "LOINC_CODE"
            display: "Observation name"
            range:
              min: LOW
              max: HIGH
            unit: "unit"
            times:
              qty: N
              lookback_months: M

          # Panel with components (e.g., blood pressure)
          - loinc: "85354-9"
            display: "Blood pressure panel"
            components:
              - loinc: "8480-6"
                display: "Systolic blood pressure"
                range:
                  min: 120
                  max: 140
                unit: "mmHg"
              - loinc: "8462-4"
                display: "Diastolic blood pressure"
                range:
                  min: 70
                  max: 90
                unit: "mmHg"
            times:
              qty: 6
              lookback_months: 12

        meds:
          - rxnorm: "RXNORM_CODE"
            display: "Medication name and strength"
            sig: "Directions for use"
            frequency: 1
            adherence:
              prob: 0.90

        encounters:
          - type:
              system: "http://snomed.info/sct"
              code: "SNOMED_CODE"
              display: "Encounter type"
            class: "AMB"
            qty: N
            spread_months: M

        procedures:
          - code:
              system: "http://snomed.info/sct"
              value: "SNOMED_CODE"
              display: "Procedure name"
            qty: N
            spread_months: M

output:
  mode: transaction
  bundle_size: 100
```

## Workflow

1. If the user specifies a persona name, use `--persona NAME`
2. If the user describes a patient scenario, check if an existing persona matches. If not, create a custom profile YAML in the project directory and use `--profile PATH`
3. Always save output to a `.json` file using `--output`
4. Validate the output with `kindling-validate`
5. Summarize what was generated (resource counts by type, key conditions, meds)

## Common FHIR Codes Reference

### Conditions (SNOMED CT)
- Hypertension: 38341003
- Type 2 Diabetes: 44054006
- Asthma: 195967001
- COPD: 13645005
- Heart Failure: 84114007
- Obesity: 414916001
- Hyperlipidemia: 55822004
- Depression: 35489007
- Anxiety: 197480006
- CKD: 709044004

### Vital Signs (LOINC)
- Blood pressure panel: 85354-9 (systolic: 8480-6, diastolic: 8462-4)
- Heart rate: 8867-4
- Respiratory rate: 9279-1
- Temperature: 8310-5
- SpO2: 2708-6
- BMI: 39156-5
- Weight: 29463-7
- Height: 8302-2

### Labs (LOINC)
- HbA1c: 4548-4
- Glucose: 2345-7
- Creatinine: 2160-0
- eGFR: 33914-3
- Total cholesterol: 2093-3
- HDL: 2085-9
- LDL: 13457-7
- Triglycerides: 2571-8
- BUN: 3094-0
- Potassium: 2823-3
- Sodium: 2951-2
- CBC WBC: 6690-2
- Hemoglobin: 718-7
- TSH: 3016-3
