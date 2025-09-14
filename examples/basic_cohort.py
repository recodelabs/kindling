#!/usr/bin/env python
"""Example of generating a cohort of patients using Kindling."""

from kindling import Generator

def main():
    # Create a profile for a diabetes cohort
    profile = {
        "version": "0.1",
        "mode": "cohort",
        "demographics": {
            "age": {
                "min": 45,
                "max": 75
            },
            "gender": {
                "distribution": {
                    "female": 0.55,
                    "male": 0.45
                }
            }
        },
        "resources": {
            "include": ["Patient", "Encounter", "Condition", "Observation", "MedicationRequest"],
            "rules": [
                {
                    "name": "diabetes_program",
                    "when": {
                        "condition": "age > 50"
                    },
                    "then": {
                        "add_conditions": [
                            {
                                "code": {
                                    "system": "http://snomed.info/sct",
                                    "value": "44054006",
                                    "display": "Type 2 diabetes mellitus"
                                },
                                "onset": {
                                    "years_ago": 5
                                }
                            }
                        ],
                        "add_observations": [
                            {
                                "loinc": "4548-4",
                                "display": "Hemoglobin A1c",
                                "range": {
                                    "min": 6.5,
                                    "max": 9.0
                                },
                                "unit": "%"
                            }
                        ],
                        "meds": [
                            {
                                "rxnorm": "860975",
                                "display": "metformin 1000 MG Oral Tablet",
                                "sig": "Take 1 tablet by mouth twice daily",
                                "frequency": 2
                            }
                        ]
                    }
                }
            ]
        },
        "output": {
            "mode": "transaction",
            "bundle_size": 50
        }
    }

    # Create generator with seed for reproducibility
    generator = Generator(profile=profile, seed=42)

    # Generate 10 patients
    bundles = generator.generate(count=10, bundle_type="transaction")

    # Output first bundle
    if isinstance(bundles, list):
        print(f"Generated {len(bundles)} bundles")
        print(f"First bundle contains {len(bundles[0].entry)} resources")
    else:
        print(f"Generated bundle with {len(bundles.entry)} resources")

    # Save to file
    with open("cohort_output.json", "w") as f:
        if isinstance(bundles, list):
            f.write(bundles[0].json(indent=2))
        else:
            f.write(bundles.json(indent=2))

    print("Bundle saved to cohort_output.json")


if __name__ == "__main__":
    main()