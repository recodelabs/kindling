# Encounter Linking Design

## Problem
Generated resources (Observations, Conditions, MedicationRequests, DiagnosticReports, Procedures) have no `encounter` reference. In FHIR R4, clinical resources should reference the Encounter during which they were recorded.

## Approach: Encounter-First Generation with Date Alignment

### Key Changes

1. **Reorder `_apply_rule()`**: Generate encounters FIRST, collect their refs and dates
2. **Align observation dates to encounters**: Instead of random dates, observations get their `effectiveDateTime` from the encounter they're linked to
3. **Add `encounter_ref` to resource factories**: `create_observation()`, `create_condition()`, `create_medication_request()`, `create_diagnostic_report()` accept optional `encounter_ref`
4. **Smart assignment**:
   - Observations/vitals: distributed across encounters, effectiveDateTime matches encounter date
   - Conditions: linked to earliest available encounter (documenting diagnosis)
   - MedicationRequests: linked to earliest encounter (when prescribed)
   - DiagnosticReports: distributed across encounters like observations
   - Procedures: matched to nearest encounter by date

### FHIR R4 Fields
- `Observation.encounter` → Reference(Encounter)
- `Condition.encounter` → Reference(Encounter)
- `MedicationRequest.encounter` → Reference(Encounter)
- `DiagnosticReport.encounter` → Reference(Encounter)
- `Procedure.encounter` → Reference(Encounter)

### No YAML Changes Required
Existing personas work as-is. Encounter linking is automatic based on temporal proximity.
