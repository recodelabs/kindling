"""Factory for creating FHIR resources."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fhir.resources.address import Address
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.encounter import Encounter
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.dosage import Dosage
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.relatedperson import RelatedPerson
from fhir.resources.diagnosticreport import DiagnosticReport

from .config import SYSTEMS, DEFAULT_ADDRESS, DEFAULT_TELECOM, RESOURCE_DEFAULTS
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
        patient_id = patient_id or self.rng.uuid()

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
                    system=SYSTEMS["MRN"],
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
        condition_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        condition_id: Optional[str] = None
    ) -> Condition:
        """Create a Condition resource.

        Args:
            patient_id: Patient ID reference
            condition_def: Condition definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            condition_id: Optional condition ID

        Returns:
            Condition resource
        """
        condition_id = condition_id or self.rng.uuid()

        # Extract code
        code_data = condition_def.get("code", {})
        coding = Coding(
            system=code_data.get("system", SYSTEMS["SNOMED"]),
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
                        system=SYSTEMS["HL7_CONDITION_CLINICAL"],
                        code=RESOURCE_DEFAULTS["CONDITION_CLINICAL_STATUS"]
                    )
                ]
            ),
            verificationStatus=CodeableConcept(
                coding=[
                    Coding(
                        system=SYSTEMS["HL7_CONDITION_VER_STATUS"],
                        code=RESOURCE_DEFAULTS["CONDITION_VERIFICATION_STATUS"]
                    )
                ]
            ),
            code=CodeableConcept(coding=[coding]),
            subject=Reference(reference=patient_ref or f"Patient/{patient_id}"),
            onsetDateTime=onset_date.strftime("%Y-%m-%d")
        )

        return condition

    def create_observation(
        self,
        patient_id: str,
        observation_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        observation_id: Optional[str] = None
    ) -> Observation:
        """Create an Observation resource.

        Args:
            patient_id: Patient ID reference
            observation_def: Observation definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            observation_id: Optional observation ID

        Returns:
            Observation resource
        """
        observation_id = observation_id or self.rng.uuid()

        # Extract code (LOINC)
        loinc_code = observation_def.get("loinc")
        coding = Coding(
            system=SYSTEMS["LOINC"],
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
            status=RESOURCE_DEFAULTS["OBSERVATION_STATUS"],
            code=CodeableConcept(coding=[coding]),
            subject=Reference(reference=patient_ref or f"Patient/{patient_id}"),
            effectiveDateTime=effective_date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            valueQuantity=quantity
        )

        return observation

    def create_medication_request(
        self,
        patient_id: str,
        medication_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        medication_id: Optional[str] = None
    ) -> MedicationRequest:
        """Create a MedicationRequest resource.

        Args:
            patient_id: Patient ID reference
            medication_def: Medication definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            medication_id: Optional medication request ID

        Returns:
            MedicationRequest resource
        """
        med_request_id = medication_id or self.rng.uuid()

        # Extract medication code (RxNorm)
        rxnorm_code = medication_def.get("rxnorm")
        coding = Coding(
            system=SYSTEMS["RXNORM"],
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
            status=RESOURCE_DEFAULTS["MEDICATION_REQUEST_STATUS"],
            intent=RESOURCE_DEFAULTS["MEDICATION_REQUEST_INTENT"],
            medication=CodeableReference(
                concept=CodeableConcept(coding=[coding])
            ),
            subject=Reference(reference=patient_ref or f"Patient/{patient_id}"),
            authoredOn=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            dosageInstruction=[dosage]
        )

        return med_request

    def create_encounter(
        self,
        patient_id: str,
        encounter_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        encounter_id: Optional[str] = None
    ) -> Encounter:
        """Create an Encounter resource.

        Args:
            patient_id: Patient ID reference
            encounter_def: Encounter definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            encounter_id: Optional encounter ID

        Returns:
            Encounter resource
        """
        encounter_id = encounter_id or self.rng.uuid()

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
            status=RESOURCE_DEFAULTS["ENCOUNTER_STATUS"],
            class_fhir=encounter_class,
            type=[encounter_type],
            subject=Reference(reference=patient_ref or f"Patient/{patient_id}"),
            period=period
        )

        return encounter

    def create_related_person(
        self,
        patient_id: str,
        related_person_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        related_person_id: Optional[str] = None
    ) -> RelatedPerson:
        """Create a RelatedPerson resource.

        Args:
            patient_id: Patient ID that this person is related to
            related_person_def: RelatedPerson definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            related_person_id: Optional RelatedPerson ID

        Returns:
            RelatedPerson resource
        """
        related_person_id = related_person_id or self.rng.uuid()

        # Extract name
        name_data = related_person_def.get("name", {})
        name = HumanName(
            family=name_data.get("family", "Doe"),
            given=name_data.get("given", ["John"])
        )

        # Extract relationship
        relationship_code = related_person_def.get("relationship")
        if isinstance(relationship_code, str):
            # Simple string relationship
            relationship_mapping = {
                "parent": ("PRN", "parent"),
                "child": ("CHILD", "child"),
                "spouse": ("SPS", "spouse"),
                "sibling": ("SIB", "sibling"),
                "guardian": ("GUARD", "guardian"),
                "emergency": ("C", "emergency contact")
            }
            code, display = relationship_mapping.get(
                relationship_code.lower(),
                (relationship_code.upper(), relationship_code)
            )
            relationship_coding = Coding(
                system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                code=code,
                display=display
            )
        else:
            # Full coding object
            relationship_coding = Coding(
                system=relationship_code.get("system", "http://terminology.hl7.org/CodeSystem/v3-RoleCode"),
                code=relationship_code.get("code"),
                display=relationship_code.get("display")
            )

        # Build identifiers if provided
        identifiers = []
        for ident_def in related_person_def.get("identifiers", []):
            identifier = Identifier(
                system=ident_def.get("system"),
                value=ident_def.get("value"),
                use=ident_def.get("use", "official")
            )
            identifiers.append(identifier)

        # Build contact info
        telecom = []
        if phone := related_person_def.get("phone"):
            telecom.append(
                ContactPoint(
                    system="phone",
                    value=phone,
                    use="home"
                )
            )
        if email := related_person_def.get("email"):
            telecom.append(
                ContactPoint(
                    system="email",
                    value=email,
                    use="home"
                )
            )

        # Create RelatedPerson
        kwargs = {
            "id": related_person_id,
            "active": related_person_def.get("active", True),
            "patient": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "relationship": [CodeableConcept(coding=[relationship_coding])],
            "name": [name],
        }

        # Add optional fields
        if identifiers:
            kwargs["identifier"] = identifiers
        if related_person_def.get("gender"):
            kwargs["gender"] = related_person_def.get("gender")
        if related_person_def.get("birthDate"):
            kwargs["birthDate"] = related_person_def.get("birthDate")
        if telecom:
            kwargs["telecom"] = telecom

        related_person = RelatedPerson(**kwargs)

        return related_person

    def create_diagnostic_report(
        self,
        patient_id: str,
        diagnostic_report_def: Dict[str, Any],
        observation_refs: Optional[List[str]] = None,
        patient_ref: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> DiagnosticReport:
        """Create a DiagnosticReport resource.

        Args:
            patient_id: Patient ID reference
            diagnostic_report_def: DiagnosticReport definition
            observation_refs: List of Observation references to include in the report
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            report_id: Optional DiagnosticReport ID

        Returns:
            DiagnosticReport resource
        """
        report_id = report_id or self.rng.uuid()

        # Extract code (usually LOINC for lab panels)
        code_data = diagnostic_report_def.get("code", {})
        coding = Coding(
            system=code_data.get("system", SYSTEMS["LOINC"]),
            code=code_data.get("value"),
            display=code_data.get("display")
        )

        # Determine status
        status = diagnostic_report_def.get("status", "final")

        # Category (e.g., LAB, RAD, etc.)
        category_data = diagnostic_report_def.get("category", {})
        if category_data:
            category_coding = Coding(
                system=category_data.get("system", "http://terminology.hl7.org/CodeSystem/v2-0074"),
                code=category_data.get("code", "LAB"),
                display=category_data.get("display", "Laboratory")
            )
            category = [CodeableConcept(coding=[category_coding])]
        else:
            # Default to LAB category
            category = [CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/v2-0074",
                    code="LAB",
                    display="Laboratory"
                )]
            )]

        # Generate issued date
        days_ago = diagnostic_report_def.get("days_ago", self.rng.randint(1, 30))
        issued_date = datetime.now() - timedelta(days=days_ago)

        # Build result references if provided
        result_refs = []
        if observation_refs:
            for obs_ref in observation_refs:
                result_refs.append(Reference(reference=obs_ref))

        # Create conclusion text if provided
        conclusion = diagnostic_report_def.get("conclusion")

        # Build the DiagnosticReport
        kwargs = {
            "id": report_id,
            "status": status,
            "category": category,
            "code": CodeableConcept(coding=[coding]),
            "subject": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "issued": issued_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        }

        # Add optional fields
        if result_refs:
            kwargs["result"] = result_refs
        if conclusion:
            kwargs["conclusion"] = conclusion

        # Add effective date if specified
        if effective_date := diagnostic_report_def.get("effectiveDateTime"):
            kwargs["effectiveDateTime"] = effective_date
        else:
            # Default to same as issued date
            kwargs["effectiveDateTime"] = issued_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        # Add performer if specified
        if performer := diagnostic_report_def.get("performer"):
            kwargs["performer"] = [Reference(reference=performer)]

        diagnostic_report = DiagnosticReport(**kwargs)

        return diagnostic_report