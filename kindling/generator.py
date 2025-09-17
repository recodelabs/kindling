"""Core Generator class for Kindling."""

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

        # Add conditions
        for condition_def in then.get("add_conditions", []):
            condition_id = self.rng.uuid()
            if request_method == "POST":
                condition_urn = self.rng.uuid()
                urn_mapping[condition_id] = condition_urn

            condition = self.resource_factory.create_condition(
                patient_id=patient.id,
                patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                condition_def=condition_def,
                condition_id=condition_id
            )
            resources.append(condition)

        # Add observations
        for obs_def in then.get("add_observations", []):
            times = obs_def.get("times") or {}
            occurrences = self._generate_time_points(times)

            for when in occurrences:
                obs_id = self.rng.uuid()
                if request_method == "POST":
                    obs_urn = self.rng.uuid()
                    urn_mapping[obs_id] = obs_urn

                observation = self.resource_factory.create_observation(
                    patient_id=patient.id,
                    patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                    observation_def=obs_def,
                    observation_id=obs_id,
                    effective_datetime=when,
                )
                resources.append(observation)

        # Add medications
        for med_def in then.get("meds", []):
            med_id = self.rng.uuid()
            if request_method == "POST":
                med_urn = self.rng.uuid()
                urn_mapping[med_id] = med_urn

            medication = self.resource_factory.create_medication_request(
                patient_id=patient.id,
                patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                medication_def=med_def,
                medication_id=med_id
            )
            resources.append(medication)

        # Add related persons with symmetrical relationships
        for related_def in then.get("related_persons", []):
            related_resources, related_urn_mapping = self._create_symmetrical_related_persons(
                patient, patient_ref, related_def, request_method
            )
            resources.extend(related_resources)
            urn_mapping.update(related_urn_mapping)

        # Add diagnostic reports
        for report_def in then.get("diagnostic_reports", []):
            report_resources, report_urn_mapping = self._create_diagnostic_report_with_observations(
                patient, patient_ref, report_def, request_method
            )
            resources.extend(report_resources)
            urn_mapping.update(report_urn_mapping)

        # Add immunizations
        for immunization_def in then.get("immunizations", []):
            # Support multiple doses of same vaccine
            qty = immunization_def.get("qty", 1)
            for i in range(qty):
                imm_id = self.rng.uuid()
                if request_method == "POST":
                    imm_urn = self.rng.uuid()
                    urn_mapping[imm_id] = imm_urn

                # Adjust days_ago for multiple doses
                if qty > 1 and "days_ago" in immunization_def:
                    # Space out multiple doses
                    adjusted_def = immunization_def.copy()
                    adjusted_def["days_ago"] = immunization_def["days_ago"] - (i * 30)
                    adjusted_def["doseNumber"] = i + 1
                else:
                    adjusted_def = immunization_def

                immunization = self.resource_factory.create_immunization(
                    patient_id=patient.id,
                    patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                    immunization_def=adjusted_def,
                    immunization_id=imm_id
                )
                resources.append(immunization)

        # Add coverage
        for coverage_def in then.get("coverage", []):
            coverage_id = self.rng.uuid()
            if request_method == "POST":
                coverage_urn = self.rng.uuid()
                urn_mapping[coverage_id] = coverage_urn

            coverage = self.resource_factory.create_coverage(
                patient_id=patient.id,
                patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                coverage_def=coverage_def,
                coverage_id=coverage_id
            )
            resources.append(coverage)

        # Add encounters
        for encounter_def in then.get("encounters", []):
            # Support multiple encounters of same type
            qty = encounter_def.get("qty", 1)
            spread_months = encounter_def.get("spread_months", 12)

            for i in range(qty):
                encounter_id = self.rng.uuid()
                if request_method == "POST":
                    encounter_urn = self.rng.uuid()
                    urn_mapping[encounter_id] = encounter_urn

                # Adjust days_ago for multiple encounters (spread them out)
                adjusted_def = encounter_def.copy()
                if qty > 1 and spread_months > 0:
                    # Spread encounters evenly over the period
                    days_between = (spread_months * 30) // qty
                    adjusted_def["days_ago"] = encounter_def.get("days_ago", 0) + (i * days_between)

                encounter = self.resource_factory.create_encounter(
                    patient_id=patient.id,
                    patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                    encounter_def=adjusted_def,
                    encounter_id=encounter_id
                )
                resources.append(encounter)

        return resources, urn_mapping

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

        # Add identifier linking to the related patient
        related_person1_def["identifiers"] = [{
            "system": "http://example.org/fhir/related-person-patient",
            "use": "official",
            "value": related_patient_id
        }]

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
        request_method: str = "POST"
    ) -> Tuple[List[Any], Dict[str, str]]:
        """Create a DiagnosticReport with associated Observations.

        Args:
            patient: Patient resource
            patient_ref: Reference to use for patient (URN UUID or regular ID)
            report_def: DiagnosticReport definition
            request_method: HTTP method for transaction bundles

        Returns:
            Tuple of (resources, urn_mapping)
        """
        resources = []
        urn_mapping = {}
        observation_refs = []

        # Create observations for the report if defined
        for obs_def in report_def.get("observations", []):
            times = obs_def.get("times") or {}
            occurrences = self._generate_time_points(times)

            for when in occurrences:
                obs_id = self.rng.uuid()
                if request_method == "POST":
                    obs_urn = self.rng.uuid()
                    urn_mapping[obs_id] = obs_urn
                    obs_ref = f"urn:uuid:{obs_urn}"
                else:
                    obs_ref = f"Observation/{obs_id}"

                observation = self.resource_factory.create_observation(
                    patient_id=patient.id,
                    patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
                    observation_def=obs_def,
                    observation_id=obs_id,
                    effective_datetime=when,
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
            patient_ref=f"urn:uuid:{patient_ref}" if request_method == "POST" else f"Patient/{patient_ref}",
            diagnostic_report_def=report_def,
            observation_refs=observation_refs,
            report_id=report_id
        )
        resources.append(diagnostic_report)

        return resources, urn_mapping

    def _generate_time_points(self, times: Dict[str, Any]) -> List[datetime]:
        """Generate timestamps for repeated resource creation."""

        qty = max(int(times.get("qty", 1)) if times else 1, 1)
        now = datetime.now()

        if not times:
            return [now - timedelta(days=self.rng.randint(1, 30)) for _ in range(qty)]

        if "days_ago" in times:
            base = int(times["days_ago"])
            if qty == 1:
                offsets = [base]
            else:
                spacing = int(times.get("spacing_days", max(base // max(qty - 1, 1), 1)))
                offsets = [base + i * spacing for i in range(qty)]
            return [now - timedelta(days=offset) for offset in offsets]

        if "lookback_months" in times:
            total_days = int(times["lookback_months"] * 30)
            if qty == 1:
                offsets = [self.rng.randint(0, max(total_days, 1))]
            else:
                step = total_days / max(qty - 1, 1)
                offsets = [int(round(i * step)) for i in range(qty)]
            return [now - timedelta(days=offset) for offset in offsets]

        if "lookback_days" in times:
            total_days = int(times["lookback_days"])
            offsets = sorted(self.rng.randint(0, max(total_days, 1)) for _ in range(qty))
            return [now - timedelta(days=offset) for offset in offsets]

        return [now - timedelta(days=self.rng.randint(1, 30)) for _ in range(qty)]

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