"""Core Generator class for Kindling."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.patient import Patient

from .bundle_assembler import BundleAssembler
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
    def from_profile(cls, profile_path: Union[str, Path], seed: Optional[int] = None):
        """Create generator from profile file.

        Args:
            profile_path: Path to YAML/JSON profile file
            seed: Random seed for deterministic generation
        """
        parser = ProfileParser()
        profile = parser.parse(profile_path)
        return cls(profile=profile, seed=seed)

    @classmethod
    def from_persona(cls, persona_name: str, seed: Optional[int] = None):
        """Create generator from built-in persona.

        Args:
            persona_name: Name of built-in persona
            seed: Random seed for deterministic generation
        """
        return cls(persona=persona_name, seed=seed)

    def set_resource_filter(self, resource_types: List[str]):
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
    ) -> Union[Bundle, List[Bundle]]:
        """Generate FHIR resources based on profile/persona.

        Args:
            count: Number of patients to generate (for cohort mode)
            bundle_type: Type of bundle ("transaction" or "collection")
            bundle_size: Maximum resources per bundle

        Returns:
            Single bundle or list of bundles
        """
        mode = self.profile.get("mode", "cohort")

        if mode == "single":
            # Generate single patient
            resources = self._generate_single_patient()
            bundle = self.bundle_assembler.create_bundle(
                resources, bundle_type=bundle_type
            )
            return bundle
        else:
            # Generate cohort
            all_resources = []
            for i in range(count):
                patient_resources = self._generate_patient(i)
                all_resources.extend(patient_resources)

            # Split into bundles if needed
            bundles = self.bundle_assembler.create_bundles(
                all_resources,
                bundle_type=bundle_type,
                bundle_size=bundle_size
            )

            return bundles[0] if len(bundles) == 1 else bundles

    def _generate_single_patient(self) -> List[Any]:
        """Generate resources for a single patient."""
        resources = []

        # Get patient definition from profile
        patient_def = self.profile.get("single_patient", {})

        # Create patient
        patient = self.resource_factory.create_patient(
            patient_def,
            patient_id=self.rng.uuid()
        )
        resources.append(patient)

        # Apply rules to generate additional resources
        rules = self.profile.get("resources", {}).get("rules", [])
        for rule in rules:
            rule_resources = self._apply_rule(rule, patient)
            resources.extend(rule_resources)

        # Filter resources if filter is set
        if self.resource_filter:
            resources = self._filter_resources(resources)

        return resources

    def _generate_patient(self, index: int) -> List[Any]:
        """Generate resources for a cohort patient."""
        resources = []

        # Generate demographics based on profile
        demographics = self._generate_demographics()

        # Create patient
        patient_id = self.rng.uuid()
        patient = self.resource_factory.create_patient(
            demographics,
            patient_id=patient_id
        )
        resources.append(patient)

        # Apply rules to generate additional resources
        rules = self.profile.get("resources", {}).get("rules", [])
        for rule in rules:
            if self._evaluate_rule_condition(rule, demographics):
                rule_resources = self._apply_rule(rule, patient)
                resources.extend(rule_resources)

        # Filter resources if filter is set
        if self.resource_filter:
            resources = self._filter_resources(resources)

        return resources

    def _generate_demographics(self) -> Dict[str, Any]:
        """Generate random demographics based on profile."""
        demo_config = self.profile.get("demographics", {})

        # Age
        age_config = demo_config.get("age", {})
        age = self.rng.randint(
            age_config.get("min", 18),
            age_config.get("max", 90)
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
            given = [self.rng.choice(["Mary", "Linda", "Sarah", "Emma", "Jennifer"])]
        else:
            given = [self.rng.choice(["John", "David", "Michael", "Robert", "William"])]

        family = self.rng.choice(["Smith", "Johnson", "Brown", "Jones", "Miller"])

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

    def _apply_rule(self, rule: Dict[str, Any], patient: Patient) -> List[Any]:
        """Apply a rule to generate resources."""
        resources = []
        then = rule.get("then", {})

        # Add conditions
        for condition_def in then.get("add_conditions", []):
            condition = self.resource_factory.create_condition(
                patient_id=patient.id,
                condition_def=condition_def
            )
            resources.append(condition)

        # Add observations
        for obs_def in then.get("add_observations", []):
            observation = self.resource_factory.create_observation(
                patient_id=patient.id,
                observation_def=obs_def
            )
            resources.append(observation)

        # Add medications
        for med_def in then.get("meds", []):
            medication = self.resource_factory.create_medication_request(
                patient_id=patient.id,
                medication_def=med_def
            )
            resources.append(medication)

        return resources

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