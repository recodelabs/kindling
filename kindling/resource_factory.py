"""Factory for creating FHIR resources."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fhir.resources.address import Address
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.encounter import Encounter, EncounterParticipant
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.dosage import Dosage
from fhir.resources.observation import Observation, ObservationComponent
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.practitioner import Practitioner
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference

from .utils.random_utils import SeededRandom


class ResourceFactory:
    """Factory for creating FHIR resources."""

    def __init__(self, rng: Optional[SeededRandom] = None):
        """Initialize resource factory.

        Args:
            rng: Seeded random generator
        """
        self.rng = rng or SeededRandom()

    def create_patient(
        self,
        patient_def: Dict[str, Any],
        patient_id: Optional[str] = None
    ) -> Patient:
        """Create a Patient resource.

        Args:
            patient_def: Patient definition dictionary
            patient_id: Optional patient ID

        Returns:
            Patient resource
        """
        patient_id = patient_id or f"patient-{self.rng.uuid()}"

        # Extract patient data
        name_data = patient_def.get("name", {})
        gender = patient_def.get("gender", "unknown")
        birth_date = patient_def.get("birthDate")

        # Build name
        name = HumanName(
            family=name_data.get("family", "Doe"),
            given=name_data.get("given", ["John"])
        )

        # Build identifiers
        identifiers = []
        for ident_def in patient_def.get("identifiers", []):
            identifier = Identifier(
                system=ident_def.get("system"),
                value=ident_def.get("value")
            )
            identifiers.append(identifier)

        # If no identifiers provided, create a default MRN
        if not identifiers:
            identifiers.append(
                Identifier(
                    system="http://hospital.example/mrn",
                    value=f"MRN-{self.rng.uuid()[:8]}"
                )
            )

        # Build address
        address_def = patient_def.get("address", {})
        if address_def:
            address = Address(
                line=address_def.get("line"),
                city=address_def.get("city"),
                state=address_def.get("state"),
                postalCode=address_def.get("postalCode"),
                country=address_def.get("country", "US")
            )
            addresses = [address]
        else:
            # Default address
            addresses = [
                Address(
                    line=["123 Main St"],
                    city="Boston",
                    state="MA",
                    postalCode="02115",
                    country="US"
                )
            ]

        # Build contact
        telecom = []
        if phone := patient_def.get("phone"):
            telecom.append(
                ContactPoint(
                    system="phone",
                    value=phone,
                    use="home"
                )
            )
        if email := patient_def.get("email"):
            telecom.append(
                ContactPoint(
                    system="email",
                    value=email,
                    use="home"
                )
            )

        # Create patient
        patient = Patient(
            id=patient_id,
            identifier=identifiers,
            name=[name],
            gender=gender,
            birthDate=birth_date,
            address=addresses,
            telecom=telecom if telecom else None
        )

        return patient

    def create_condition(
        self,
        patient_id: str,
        condition_def: Dict[str, Any]
    ) -> Condition:
        """Create a Condition resource.

        Args:
            patient_id: Patient ID reference
            condition_def: Condition definition

        Returns:
            Condition resource
        """
        condition_id = f"condition-{self.rng.uuid()}"

        # Extract code
        code_data = condition_def.get("code", {})
        coding = Coding(
            system=code_data.get("system", "http://snomed.info/sct"),
            code=code_data.get("value"),
            display=code_data.get("display")
        )

        # Calculate onset date
        onset = condition_def.get("onset", {})
        if years_ago := onset.get("years_ago"):
            onset_date = datetime.now() - timedelta(days=years_ago * 365)
        else:
            onset_date = datetime.now() - timedelta(days=365)  # Default 1 year ago

        # Create condition
        condition = Condition(
            id=condition_id,
            clinicalStatus=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                        code="active"
                    )
                ]
            ),
            verificationStatus=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        code="confirmed"
                    )
                ]
            ),
            code=CodeableConcept(coding=[coding]),
            subject=Reference(reference=f"Patient/{patient_id}"),
            onsetDateTime=onset_date.strftime("%Y-%m-%d")
        )

        return condition

    def create_observation(
        self,
        patient_id: str,
        observation_def: Dict[str, Any]
    ) -> Observation:
        """Create an Observation resource.

        Args:
            patient_id: Patient ID reference
            observation_def: Observation definition

        Returns:
            Observation resource
        """
        observation_id = f"observation-{self.rng.uuid()}"

        # Extract code (LOINC)
        loinc_code = observation_def.get("loinc")
        coding = Coding(
            system="http://loinc.org",
            code=loinc_code,
            display=observation_def.get("display", "")
        )

        # Generate value within range
        value_range = observation_def.get("range", {})
        min_val = value_range.get("min", 0)
        max_val = value_range.get("max", 100)
        value = self.rng.uniform(min_val, max_val)

        # Create quantity
        unit = observation_def.get("unit", "1")
        if not unit:
            unit = "1"  # Default unit if empty
        quantity = Quantity(
            value=round(value, 2),
            unit=unit,
            system="http://unitsofmeasure.org",
            code=unit
        )

        # Generate effective date (recent)
        days_ago = self.rng.randint(1, 30)
        effective_date = datetime.now() - timedelta(days=days_ago)

        # Create observation
        observation = Observation(
            id=observation_id,
            status="final",
            code=CodeableConcept(coding=[coding]),
            subject=Reference(reference=f"Patient/{patient_id}"),
            effectiveDateTime=effective_date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            valueQuantity=quantity
        )

        return observation

    def create_medication_request(
        self,
        patient_id: str,
        medication_def: Dict[str, Any]
    ) -> MedicationRequest:
        """Create a MedicationRequest resource.

        Args:
            patient_id: Patient ID reference
            medication_def: Medication definition

        Returns:
            MedicationRequest resource
        """
        med_request_id = f"medicationrequest-{self.rng.uuid()}"

        # Extract medication code (RxNorm)
        rxnorm_code = medication_def.get("rxnorm")
        coding = Coding(
            system="http://www.nlm.nih.gov/research/umls/rxnorm",
            code=rxnorm_code,
            display=medication_def.get("display", "")
        )

        # Create dosage instruction
        frequency = medication_def.get("frequency", 1)
        # Ensure frequency is an integer
        if frequency < 1:
            frequency = 1  # PRN medications
        else:
            frequency = int(frequency)

        dosage = Dosage(
            text=medication_def.get("sig", "Take as directed"),
            timing={
                "repeat": {
                    "frequency": frequency,
                    "period": 1,
                    "periodUnit": "d"
                }
            }
        )

        # Create medication request
        med_request = MedicationRequest(
            id=med_request_id,
            status="active",
            intent="order",
            medication=CodeableReference(
                concept=CodeableConcept(coding=[coding])
            ),
            subject=Reference(reference=f"Patient/{patient_id}"),
            authoredOn=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            dosageInstruction=[dosage]
        )

        return med_request

    def create_encounter(
        self,
        patient_id: str,
        encounter_def: Dict[str, Any]
    ) -> Encounter:
        """Create an Encounter resource.

        Args:
            patient_id: Patient ID reference
            encounter_def: Encounter definition

        Returns:
            Encounter resource
        """
        encounter_id = f"encounter-{self.rng.uuid()}"

        # Encounter class
        encounter_class = Coding(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code=encounter_def.get("class", "AMB"),
            display=encounter_def.get("class_display", "ambulatory")
        )

        # Encounter type
        type_code = encounter_def.get("type", {})
        if type_code:
            encounter_type = CodeableConcept(
                coding=[
                    Coding(
                        system=type_code.get("system", "http://snomed.info/sct"),
                        code=type_code.get("code"),
                        display=type_code.get("display")
                    )
                ]
            )
        else:
            # Default to general examination
            encounter_type = CodeableConcept(
                coding=[
                    Coding(
                        system="http://snomed.info/sct",
                        code="162673000",
                        display="General examination"
                    )
                ]
            )

        # Period
        days_ago = encounter_def.get("days_ago", self.rng.randint(1, 90))
        start_time = datetime.now() - timedelta(days=days_ago)
        end_time = start_time + timedelta(hours=1)

        period = Period(
            start=start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            end=end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        )

        # Create encounter
        encounter = Encounter(
            id=encounter_id,
            status="finished",
            class_fhir=encounter_class,
            type=[encounter_type],
            subject=Reference(reference=f"Patient/{patient_id}"),
            period=period
        )

        return encounter