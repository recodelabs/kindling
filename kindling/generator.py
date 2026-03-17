"""Core Generator class for Kindling."""

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient

from .bundle_assembler import BundleAssembler
from .config import DEMOGRAPHICS
from .persona_loader import PersonaLoader
from .profile_parser import ProfileParser
from .resource_factory import ResourceFactory
from .utils.random_utils import SeededRandom


class Generator:
    """Main generator class for creating synthetic FHIR data."""

    def __init__(
        self,
        profile: Optional[Dict[str, Any]] = None,
        persona: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        """Initialize generator with profile or persona.

        Args:
            profile: Profile dictionary defining generation parameters
            persona: Name of built-in persona to use
            seed: Random seed for deterministic generation
        """
        if profile and persona:
            raise ValueError("Cannot specify both profile and persona")

        if not profile and not persona:
            raise ValueError("Must specify either profile or persona")

        self.profile = profile
        self.persona_name = persona
        self.seed = seed
        self.rng = SeededRandom(seed)
        self.resource_filter = None  # Optional filter for resource types

        # Initialize components
        self.resource_factory = ResourceFactory(self.rng)
        self.bundle_assembler = BundleAssembler()

        # Load persona if specified
        if persona:
            self.persona_loader = PersonaLoader()
            self.persona_data = self.persona_loader.load(persona)
            # Convert persona to profile format
            self.profile = self._persona_to_profile(self.persona_data)

    @classmethod
    def from_profile(cls, profile_path: Union[str, Path], seed: Optional[int] = None) -> "Generator":
        """Create generator from profile file.

        Args:
            profile_path: Path to YAML/JSON profile file
            seed: Random seed for deterministic generation
        """
        parser = ProfileParser()
        profile = parser.parse(profile_path)
        return cls(profile=profile, seed=seed)

    @classmethod
    def from_persona(cls, persona_name: str, seed: Optional[int] = None) -> "Generator":
        """Create generator from built-in persona.

        Args:
            persona_name: Name of built-in persona
            seed: Random seed for deterministic generation
        """
        return cls(persona=persona_name, seed=seed)

    def set_resource_filter(self, resource_types: List[str]) -> None:
        """Set filter for which resource types to include.

        Args:
            resource_types: List of resource type names to include (e.g., ["Patient", "Condition"])
        """
        self.resource_filter = resource_types

    def generate(
        self,
        count: int = 1,
        bundle_type: str = "transaction",
        bundle_size: int = 100,
        request_method: str = "POST",
    ) -> Union[Bundle, List[Bundle]]:
        """Generate FHIR resources based on profile/persona.

        Args:
            count: Number of patients to generate (for cohort mode)
            bundle_type: Type of bundle ("transaction" or "collection")
            bundle_size: Maximum resources per bundle
            request_method: HTTP method for transaction bundles ("POST" or "PUT")

        Returns:
            Single bundle or list of bundles
        """
        mode = self.profile.get("mode", "cohort")

        if mode == "single":
            # Generate single patient
            resources, urn_mapping = self._generate_single_patient(request_method)
            bundle = self.bundle_assembler.create_bundle(
                resources, bundle_type=bundle_type, request_method=request_method,
                urn_mapping=urn_mapping
            )
            return bundle
        else:
            # Generate cohort
            all_resources = []
            all_urn_mappings = {}
            for i in range(count):
                patient_resources, urn_mapping = self._generate_patient(i, request_method)
                all_resources.extend(patient_resources)
                all_urn_mappings.update(urn_mapping)

            # Split into bundles if needed
            bundles = self.bundle_assembler.create_bundles(
                all_resources,
                bundle_type=bundle_type,
                bundle_size=bundle_size,
                request_method=request_method,
                urn_mapping=all_urn_mappings
            )

            return bundles[0] if len(bundles) == 1 else bundles

    def _generate_single_patient(self, request_method: str = "POST") -> Tuple[List[Any], Dict[str, str]]:
        """Generate resources for a single patient.

        Args:
            request_method: HTTP method for transaction bundles

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}

        # Get patient definition from profile
        patient_def = self.profile.get("single_patient", {})

        # Generate IDs
        patient_id = self.rng.uuid()
        patient_urn = self.rng.uuid() if request_method == "POST" else patient_id

        # Track URN mapping for POST method
        if request_method == "POST":
            urn_mapping[patient_id] = patient_urn

        # Create patient
        patient = self.resource_factory.create_patient(
            patient_def,
            patient_id=patient_id
        )
        resources.append(patient)

        # Apply rules to generate additional resources
        rules = self.profile.get("resources", {}).get("rules", [])
        for rule in rules:
            rule_resources, rule_urn_mapping = self._apply_rule(
                rule, patient, patient_urn if request_method == "POST" else patient_id, request_method
            )
            resources.extend(rule_resources)
            urn_mapping.update(rule_urn_mapping)

        # Filter resources if filter is set
        if self.resource_filter:
            resources = self._filter_resources(resources)

        return resources, urn_mapping

    def _generate_patient(self, index: int, request_method: str = "POST") -> Tuple[List[Any], Dict[str, str]]:
        """Generate resources for a cohort patient.

        Args:
            index: Patient index in cohort
            request_method: HTTP method for transaction bundles

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}

        # Generate demographics based on profile
        demographics = self._generate_demographics()

        # Generate IDs
        patient_id = self.rng.uuid()
        patient_urn = self.rng.uuid() if request_method == "POST" else patient_id

        # Track URN mapping for POST method
        if request_method == "POST":
            urn_mapping[patient_id] = patient_urn

        # Create patient
        patient = self.resource_factory.create_patient(
            demographics,
            patient_id=patient_id
        )
        resources.append(patient)

        # Apply rules to generate additional resources
        rules = self.profile.get("resources", {}).get("rules", [])
        for rule in rules:
            if self._evaluate_rule_condition(rule, demographics):
                rule_resources, rule_urn_mapping = self._apply_rule(
                    rule, patient, patient_urn if request_method == "POST" else patient_id, request_method
                )
                resources.extend(rule_resources)
                urn_mapping.update(rule_urn_mapping)

        # Filter resources if filter is set
        if self.resource_filter:
            resources = self._filter_resources(resources)

        return resources, urn_mapping

    def _generate_demographics(self) -> Dict[str, Any]:
        """Generate random demographics based on profile."""
        demo_config = self.profile.get("demographics", {})

        # Age
        age_config = demo_config.get("age", {})
        age = self.rng.randint(
            age_config.get("min", DEMOGRAPHICS["DEFAULT_AGE_MIN"]),
            age_config.get("max", DEMOGRAPHICS["DEFAULT_AGE_MAX"])
        )

        # Gender
        gender_dist = demo_config.get("gender", {}).get("distribution", {})
        if gender_dist:
            gender = self.rng.weighted_choice(gender_dist)
        else:
            gender = self.rng.choice(["male", "female"])

        # Birth date from age
        today = datetime.now()
        birth_date = today - timedelta(days=age * 365)

        # Generate name
        if gender == "female":
            given = [self.rng.choice(DEMOGRAPHICS["FEMALE_NAMES"])]
        else:
            given = [self.rng.choice(DEMOGRAPHICS["MALE_NAMES"])]

        family = self.rng.choice(DEMOGRAPHICS["FAMILY_NAMES"])

        return {
            "age": age,
            "gender": gender,
            "birthDate": birth_date.strftime("%Y-%m-%d"),
            "name": {
                "given": given,
                "family": family
            }
        }

    def _evaluate_rule_condition(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate if a rule condition is met."""
        when = rule.get("when", {})
        condition = when.get("condition", "true")

        # Simple evaluation for now
        if condition == "true":
            return True

        # Basic age comparison
        if "age >" in condition:
            age_threshold = int(condition.split(">")[1].strip())
            return context.get("age", 0) > age_threshold

        return False

    def _apply_rule(self, rule: Dict[str, Any], patient: Patient, patient_ref: str, request_method: str = "POST") -> Tuple[List[Any], Dict[str, str]]:
        """Apply a rule to generate resources.

        Encounters are generated first so that clinical resources (observations,
        conditions, medications, diagnostic reports) can reference them. Each
        clinical resource is assigned to the nearest encounter by date.

        Args:
            rule: Rule definition
            patient: Patient resource
            patient_ref: Reference to use for patient (URN UUID or regular ID)
            request_method: HTTP method for transaction bundles

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}
        then = rule.get("then", {})
        patient_fhir_ref = f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}"

        # --- 1. Generate encounters FIRST so we can link other resources ---
        encounter_info = []  # List of (encounter_ref_url, encounter_date)
        for encounter_def in then.get("encounters", []):
            qty = encounter_def.get("qty", 1)
            spread_months = encounter_def.get("spread_months", 12)

            for i in range(qty):
                encounter_id = self.rng.uuid()
                if request_method == "POST":
                    encounter_urn = self.rng.uuid()
                    urn_mapping[encounter_id] = encounter_urn

                adjusted_def = encounter_def.copy()
                if qty > 1 and spread_months > 0:
                    days_between = (spread_months * 30) // qty
                    adjusted_def["days_ago"] = encounter_def.get("days_ago", 0) + (i * days_between)

                # Calculate encounter date for linking
                days_ago = adjusted_def.get("days_ago", self.rng.randint(1, 90))
                encounter_date = datetime.now() - timedelta(days=days_ago)

                encounter = self.resource_factory.create_encounter(
                    patient_id=patient.id,
                    patient_ref=patient_fhir_ref,
                    encounter_def=adjusted_def,
                    encounter_id=encounter_id
                )
                resources.append(encounter)

                # Build the reference URL that other resources will use
                if request_method == "POST":
                    enc_ref_url = f"urn:uuid:{encounter_urn}"
                else:
                    enc_ref_url = f"Encounter/{encounter_id}"
                encounter_info.append((enc_ref_url, encounter_date))

        # Sort encounters by date (most recent first) for assignment
        encounter_info.sort(key=lambda x: x[1], reverse=True)

        def _pick_encounter(target_date: datetime) -> Optional[str]:
            """Find the encounter closest to target_date."""
            if not encounter_info:
                return None
            return min(encounter_info, key=lambda x: abs((x[1] - target_date).total_seconds()))[0]

        def _pick_encounter_with_date(target_date: datetime) -> Tuple[Optional[str], Optional[datetime]]:
            """Find the encounter closest to target_date, return (ref, date)."""
            if not encounter_info:
                return None, None
            best = min(encounter_info, key=lambda x: abs((x[1] - target_date).total_seconds()))
            return best[0], best[1]

        def _distribute_across_encounters(count: int) -> List[Tuple[str, datetime]]:
            """Distribute items across encounters round-robin, returning (ref, date) pairs."""
            if not encounter_info:
                return [(None, datetime.now() - timedelta(days=self.rng.randint(1, 30)))] * count
            result = []
            for i in range(count):
                idx = i % len(encounter_info)
                result.append(encounter_info[idx])
            return result

        # --- 2. Add conditions (linked to earliest encounter = diagnosis visit) ---
        for condition_def in then.get("add_conditions", []):
            condition_id = self.rng.uuid()
            if request_method == "POST":
                condition_urn = self.rng.uuid()
                urn_mapping[condition_id] = condition_urn

            # Link to closest encounter by onset date
            onset = condition_def.get("onset", {})
            if onset.get("years_ago") is not None:
                onset_date = datetime.now() - timedelta(days=onset["years_ago"] * 365)
            elif onset.get("days_ago") is not None:
                onset_date = datetime.now() - timedelta(days=onset["days_ago"])
            else:
                onset_date = datetime.now() - timedelta(days=365)
            enc_ref = _pick_encounter(onset_date)

            condition = self.resource_factory.create_condition(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                condition_def=condition_def,
                condition_id=condition_id,
                encounter_ref=enc_ref,
            )
            resources.append(condition)

        # --- 3. Add observations (aligned to encounter dates) ---
        # Each obs_def is expanded independently (via times.qty) and matched
        # to encounters by expected date so trending series stay coherent.
        for obs_def in then.get("add_observations", []):
            times = obs_def.get("times")
            expanded = self._expand_observation_defs([obs_def])
            qty = len(expanded)

            if qty > 1 and encounter_info and times:
                # Assign observations proportionally across encounters.
                # Both are ordered newest-first, so obs[0] (end value) gets
                # the most recent encounter, obs[-1] (start value) gets oldest.
                n_enc = len(encounter_info)
                for i, exp_obs_def in enumerate(expanded):
                    # Evenly space across available encounters
                    idx = min(int(i * n_enc / qty), n_enc - 1)
                    enc_ref, enc_date = encounter_info[idx]

                    obs_id = self.rng.uuid()
                    if request_method == "POST":
                        obs_urn = self.rng.uuid()
                        urn_mapping[obs_id] = obs_urn

                    observation = self.resource_factory.create_observation(
                        patient_id=patient.id,
                        patient_ref=patient_fhir_ref,
                        observation_def=exp_obs_def,
                        observation_id=obs_id,
                        encounter_ref=enc_ref,
                        effective_datetime=enc_date,
                    )
                    resources.append(observation)
            else:
                # Single observation — match by days_ago if specified, else round-robin
                obs_days_ago = (times or {}).get("days_ago") if times else None
                if obs_days_ago is not None and encounter_info:
                    target_date = datetime.now() - timedelta(days=obs_days_ago)
                    enc_ref, enc_date = _pick_encounter_with_date(target_date)
                    assignments = [(enc_ref, enc_date)] * qty
                else:
                    assignments = _distribute_across_encounters(qty)
                for exp_obs_def, (enc_ref, enc_date) in zip(expanded, assignments):
                    obs_id = self.rng.uuid()
                    if request_method == "POST":
                        obs_urn = self.rng.uuid()
                        urn_mapping[obs_id] = obs_urn

                    observation = self.resource_factory.create_observation(
                        patient_id=patient.id,
                        patient_ref=patient_fhir_ref,
                        observation_def=exp_obs_def,
                        observation_id=obs_id,
                        encounter_ref=enc_ref,
                        effective_datetime=enc_date,
                    )
                    resources.append(observation)

        # --- 4. Add medications (linked to earliest/most recent encounter) ---
        for med_def in then.get("meds", []):
            med_id = self.rng.uuid()
            if request_method == "POST":
                med_urn = self.rng.uuid()
                urn_mapping[med_id] = med_urn

            # Link to earliest encounter (when medication was first prescribed)
            enc_ref = encounter_info[-1][0] if encounter_info else None

            medication = self.resource_factory.create_medication_request(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                medication_def=med_def,
                medication_id=med_id,
                encounter_ref=enc_ref,
            )
            resources.append(medication)

        # --- 4b. Add medication statements (what patient is currently taking) ---
        for med_def in then.get("medication_statements", []):
            med_id = self.rng.uuid()
            if request_method == "POST":
                med_urn = self.rng.uuid()
                urn_mapping[med_id] = med_urn

            enc_ref = encounter_info[-1][0] if encounter_info else None

            med_stmt = self.resource_factory.create_medication_statement(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                medication_def=med_def,
                medication_id=med_id,
                encounter_ref=enc_ref,
            )
            resources.append(med_stmt)

        # --- 5. Add related persons (no encounter link needed) ---
        for related_def in then.get("related_persons", []):
            related_resources, related_urn_mapping = self._create_symmetrical_related_persons(
                patient, patient_ref, related_def, request_method
            )
            resources.extend(related_resources)
            urn_mapping.update(related_urn_mapping)

        # --- 6. Add diagnostic reports (distributed across encounters) ---
        for report_def in then.get("diagnostic_reports", []):
            report_resources, report_urn_mapping = self._create_diagnostic_report_with_observations(
                patient, patient_ref, report_def, request_method,
                encounter_info=encounter_info,
            )
            resources.extend(report_resources)
            urn_mapping.update(report_urn_mapping)

        # --- 7. Add immunizations (no encounter link for now) ---
        for immunization_def in then.get("immunizations", []):
            qty = immunization_def.get("qty", 1)
            for i in range(qty):
                imm_id = self.rng.uuid()
                if request_method == "POST":
                    imm_urn = self.rng.uuid()
                    urn_mapping[imm_id] = imm_urn

                if qty > 1 and "days_ago" in immunization_def:
                    adjusted_def = immunization_def.copy()
                    adjusted_def["days_ago"] = immunization_def["days_ago"] - (i * 30)
                    adjusted_def["doseNumber"] = i + 1
                else:
                    adjusted_def = immunization_def

                immunization = self.resource_factory.create_immunization(
                    patient_id=patient.id,
                    patient_ref=patient_fhir_ref,
                    immunization_def=adjusted_def,
                    immunization_id=imm_id
                )
                resources.append(immunization)

        # --- 8. Add coverage (no encounter link) ---
        for coverage_def in then.get("coverage", []):
            coverage_id = self.rng.uuid()
            if request_method == "POST":
                coverage_urn = self.rng.uuid()
                urn_mapping[coverage_id] = coverage_urn

            coverage = self.resource_factory.create_coverage(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                coverage_def=coverage_def,
                coverage_id=coverage_id
            )
            resources.append(coverage)

        # --- 9. Add allergies ---
        for allergy_def in then.get("allergies", []):
            allergy_id = self.rng.uuid()
            if request_method == "POST":
                allergy_urn = self.rng.uuid()
                urn_mapping[allergy_id] = allergy_urn

            # Link to earliest encounter (when allergy was documented)
            enc_ref = encounter_info[-1][0] if encounter_info else None

            allergy = self.resource_factory.create_allergy_intolerance(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                allergy_def=allergy_def,
                allergy_id=allergy_id,
                encounter_ref=enc_ref,
            )
            resources.append(allergy)

        return resources, urn_mapping

    def _expand_observation_defs(self, obs_defs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Expand observation definitions that have times.qty into individual obs defs.

        Handles trending values: if a component or simple value has a 'trend'
        field with 'start' and 'end', values are linearly interpolated across
        the expanded observations (oldest to newest).

        Args:
            obs_defs: List of observation definitions, some may have times.qty

        Returns:
            Expanded list of individual observation definitions
        """
        expanded = []
        for obs_def in obs_defs:
            times = obs_def.get("times")
            if not times or times.get("qty", 1) <= 1:
                expanded.append(obs_def)
                continue

            qty = times["qty"]
            for i in range(qty):
                # factor goes from 1.0 (newest/end value) to 0.0 (oldest/start value)
                # because encounters are sorted most-recent-first
                factor = 1.0 - (i / (qty - 1)) if qty > 1 else 1.0
                obs_copy = deepcopy(obs_def)
                # Remove times from the copy so it's not re-expanded
                obs_copy.pop("times", None)

                # Interpolate trending values for components
                if "components" in obs_copy:
                    for comp in obs_copy["components"]:
                        if "trend" in comp:
                            start = comp["trend"]["start"]
                            end = comp["trend"]["end"]
                            comp["value"] = round(start + (end - start) * factor, 1)
                            comp.pop("trend", None)
                            comp.pop("range", None)

                # Interpolate trending values for simple observations
                if "trend" in obs_copy:
                    start = obs_copy["trend"]["start"]
                    end = obs_copy["trend"]["end"]
                    obs_copy["value"] = round(start + (end - start) * factor, 1)
                    obs_copy.pop("trend", None)
                    obs_copy.pop("range", None)

                expanded.append(obs_copy)

        return expanded

    def _persona_to_profile(self, persona_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert persona data to profile format."""
        return {
            "version": "0.1",
            "mode": "single",
            "single_patient": persona_data.get("patient", {}),
            "resources": persona_data.get("resources", {}),
            "output": persona_data.get("output", {
                "mode": "transaction",
                "bundle_size": 100
            })
        }

    def _create_symmetrical_related_persons(
        self,
        patient: Patient,
        patient_ref: str,
        related_def: Dict[str, Any],
        request_method: str = "POST"
    ) -> Tuple[List[Any], Dict[str, str]]:
        """Create symmetrical RelatedPerson resources.

        Creates two RelatedPerson resources:
        1. The related person linked to the main patient
        2. A new Patient for the related person, and a RelatedPerson linking back

        Args:
            patient: Main patient resource
            patient_ref: Reference to use for patient (URN UUID or regular ID)
            related_def: Related person definition
            request_method: HTTP method for transaction bundles

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}

        # Create the related person's Patient resource
        related_patient_id = self.rng.uuid()
        related_patient_urn = self.rng.uuid() if request_method == "POST" else related_patient_id

        if request_method == "POST":
            urn_mapping[related_patient_id] = related_patient_urn

        # Create Patient for the related person
        related_patient_def = {
            "name": related_def.get("name", {}),
            "gender": related_def.get("gender", "unknown"),
            "birthDate": related_def.get("birthDate")
        }

        # Add identifiers if provided
        if "identifiers" in related_def:
            related_patient_def["identifiers"] = related_def["identifiers"]

        # Add contact info if provided
        if "phone" in related_def:
            related_patient_def["phone"] = related_def["phone"]
        if "email" in related_def:
            related_patient_def["email"] = related_def["email"]

        related_patient = self.resource_factory.create_patient(
            related_patient_def,
            patient_id=related_patient_id
        )
        resources.append(related_patient)

        # Create RelatedPerson from related patient to main patient
        related_person1_id = self.rng.uuid()
        if request_method == "POST":
            related_person1_urn = self.rng.uuid()
            urn_mapping[related_person1_id] = related_person1_urn

        # Map relationships to their inverses
        inverse_relationship = {
            "parent": "child",
            "child": "parent",
            "spouse": "spouse",
            "sibling": "sibling",
            "guardian": "child",
            "emergency": "emergency"
        }

        original_relationship = related_def.get("relationship", "").lower()
        inverse_rel = inverse_relationship.get(original_relationship, original_relationship)

        # Create first RelatedPerson (related person -> main patient)
        related_person1_def = {
            "name": related_def.get("name", {}),
            "relationship": related_def.get("relationship"),
            "active": related_def.get("active", True),
            "gender": related_def.get("gender"),
            "birthDate": related_def.get("birthDate")
        }

        # Preserve any user-specified identifiers while adding the linking identifier
        identifiers = deepcopy(related_def.get("identifiers") or [])
        identifiers.append({
            "system": "http://example.org/fhir/related-person-patient",
            "use": "official",
            "value": related_patient_id
        })
        related_person1_def["identifiers"] = identifiers

        related_person1 = self.resource_factory.create_related_person(
            patient_id=patient.id,
            patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
            related_person_def=related_person1_def,
            related_person_id=related_person1_id
        )
        resources.append(related_person1)

        # Create second RelatedPerson (main patient -> related patient)
        related_person2_id = self.rng.uuid()
        if request_method == "POST":
            related_person2_urn = self.rng.uuid()
            urn_mapping[related_person2_id] = related_person2_urn

        # Get main patient's name
        patient_name = {}
        if patient.name and len(patient.name) > 0:
            patient_name = {
                "family": patient.name[0].family,
                "given": patient.name[0].given
            }

        related_person2_def = {
            "name": patient_name,
            "relationship": inverse_rel,
            "active": True,
            "gender": patient.gender,
            "birthDate": patient.birthDate
        }

        # Add identifier linking to the main patient
        related_person2_def["identifiers"] = [{
            "system": "http://example.org/fhir/related-person-patient",
            "use": "official",
            "value": patient.id
        }]

        related_person2 = self.resource_factory.create_related_person(
            patient_id=related_patient_id,
            patient_ref=f"urn:uuid:{related_patient_urn}" if request_method == "POST" else f"Patient/{related_patient_id}",
            related_person_def=related_person2_def,
            related_person_id=related_person2_id
        )
        resources.append(related_person2)

        return resources, urn_mapping

    def _create_diagnostic_report_with_observations(
        self,
        patient: Patient,
        patient_ref: str,
        report_def: Dict[str, Any],
        request_method: str = "POST",
        encounter_info: Optional[List[Tuple[str, datetime]]] = None,
    ) -> Tuple[List[Any], Dict[str, str]]:
        """Create a DiagnosticReport with associated Observations.

        Args:
            patient: Patient resource
            patient_ref: Reference to use for patient (URN UUID or regular ID)
            report_def: DiagnosticReport definition
            request_method: HTTP method for transaction bundles
            encounter_info: List of (encounter_ref_url, encounter_date) for linking

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}
        observation_refs = []
        patient_fhir_ref = f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}"

        # Pick an encounter for this report
        enc_ref = None
        enc_date = None
        if encounter_info:
            report_days_ago = report_def.get("days_ago")
            if report_days_ago is not None:
                # Match to the closest encounter by date
                target_date = datetime.now() - timedelta(days=report_days_ago)
                enc_ref, enc_date = min(
                    encounter_info,
                    key=lambda ei: abs((ei[1] - target_date).total_seconds()),
                )
            else:
                # Default to the most recent encounter
                enc_ref, enc_date = encounter_info[0]

        # Create observations for the report if defined
        for obs_def in report_def.get("observations", []):
            obs_id = self.rng.uuid()
            if request_method == "POST":
                obs_urn = self.rng.uuid()
                urn_mapping[obs_id] = obs_urn
            obs_ref = f"Observation/{obs_id}"

            observation = self.resource_factory.create_observation(
                patient_id=patient.id,
                patient_ref=patient_fhir_ref,
                observation_def=obs_def,
                observation_id=obs_id,
                encounter_ref=enc_ref,
                effective_datetime=enc_date,
            )
            resources.append(observation)
            observation_refs.append(obs_ref)

        # Create the diagnostic report
        report_id = self.rng.uuid()
        if request_method == "POST":
            report_urn = self.rng.uuid()
            urn_mapping[report_id] = report_urn

        diagnostic_report = self.resource_factory.create_diagnostic_report(
            patient_id=patient.id,
            patient_ref=patient_fhir_ref,
            diagnostic_report_def=report_def,
            observation_refs=observation_refs,
            report_id=report_id,
            encounter_ref=enc_ref,
        )
        resources.append(diagnostic_report)

        return resources, urn_mapping

    def _filter_resources(self, resources: List[Any]) -> List[Any]:
        """Filter resources based on resource_filter.

        Args:
            resources: List of resources to filter

        Returns:
            Filtered list of resources
        """
        if not self.resource_filter:
            return resources

        filtered = []
        for resource in resources:
            resource_type = resource.__class__.__name__
            if resource_type in self.resource_filter:
                filtered.append(resource)

        # Always include Patient if any resources are requested
        # (since other resources reference the Patient)
        if filtered and not any(r.__class__.__name__ == "Patient" for r in filtered):
            for resource in resources:
                if resource.__class__.__name__ == "Patient":
                    filtered.insert(0, resource)
                    break

        return filtered