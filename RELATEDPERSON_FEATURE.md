# RelatedPerson Support in Kindling

## Overview
Kindling now supports the generation of FHIR RelatedPerson resources with automatic symmetrical relationship creation. When defining a related person for a patient, the system automatically creates:

1. A new Patient resource for the related person
2. Two RelatedPerson resources establishing the bidirectional relationship

## Symmetrical Relationships

The following relationships are supported with automatic inverse mapping:
- `parent` ↔ `child`
- `child` ↔ `parent`
- `spouse` ↔ `spouse`
- `sibling` ↔ `sibling`
- `guardian` ↔ `child`
- `emergency` ↔ `emergency`

## Usage Example

In your YAML profile, add related persons under the `then` section of a rule:

```yaml
resources:
  rules:
    - name: family_relationships
      when:
        condition: "true"
      then:
        related_persons:
          - name:
              family: "Berg"
              given: ["Anouk"]
            relationship: "child"
            gender: "female"
            birthDate: "2015-06-20"
```

This will generate:
1. A Patient resource for Anouk Berg
2. A RelatedPerson resource linking Anouk as a child of the main patient
3. A RelatedPerson resource linking the main patient as a parent of Anouk

## Resource Structure

Each RelatedPerson resource includes:
- Reference to the Patient it relates to
- The relationship type (using HL7 v3-RoleCode terminology)
- Name and demographics of the related person
- Optional identifiers linking to the corresponding Patient resource
- Optional contact information (phone, email)

## Example Files

See `example_related_person.yaml` for a complete example demonstrating family relationships including children and spouse.