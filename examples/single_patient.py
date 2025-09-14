#!/usr/bin/env python
"""Example of generating a single patient using a persona."""

from kindling import Generator

def main():
    # Generate Mary with diabetes using built-in persona
    print("Generating Mary with Type 2 Diabetes...")
    generator = Generator.from_persona("mary_diabetes", seed=42)
    bundle = generator.generate()

    print(f"Generated bundle with {len(bundle.entry)} resources")

    # Save to file
    with open("mary_output.json", "w") as f:
        f.write(bundle.json(indent=2))

    print("Bundle saved to mary_output.json")

    # Generate John with asthma
    print("\nGenerating John with Asthma...")
    generator = Generator.from_persona("john_asthma", seed=43)
    bundle = generator.generate()

    print(f"Generated bundle with {len(bundle.entry)} resources")

    # Save to file
    with open("john_output.json", "w") as f:
        f.write(bundle.json(indent=2))

    print("Bundle saved to john_output.json")


if __name__ == "__main__":
    main()