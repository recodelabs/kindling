"""Factory for creating FHIR resources."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fhir.resources.address import Address
from fhir.resources.annotation import Annotation
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
from fhir.resources.duration import Duration
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.relatedperson import RelatedPerson
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.immunization import Immunization
from fhir.resources.coverage import Coverage

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

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Return an ISO 8601 timestamp in UTC format expected by FHIR."""

        return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S+00:00")

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
                    line=DEFAULT_ADDRESS["LINE"],
                    city=DEFAULT_ADDRESS["CITY"],
                    state=DEFAULT_ADDRESS["STATE"],
                    postalCode=DEFAULT_ADDRESS["POSTAL_CODE"],
                    country=DEFAULT_ADDRESS["COUNTRY"]
                )
            ]

        # Build contact
        telecom: List[ContactPoint] = []

        for telecom_entry in patient_def.get("telecom", []):
            telecom.append(
                ContactPoint(
                    system=telecom_entry.get("system"),
                    value=telecom_entry.get("value"),
                    use=telecom_entry.get("use")
                )
            )

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

        if not telecom and DEFAULT_TELECOM:
            for telecom_entry in DEFAULT_TELECOM:
                telecom.append(
                    ContactPoint(
                        system=telecom_entry.get("system"),
                        value=telecom_entry.get("value"),
                        use=telecom_entry.get("use")
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

        if isinstance(patient.birthDate, date):
            patient.__dict__["birthDate"] = patient.birthDate.isoformat()

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
        observation_id: Optional[str] = None,
        effective_datetime: Optional[datetime] = None,
    ) -> Observation:
        """Create an Observation resource.

        Args:
            patient_id: Patient ID reference
            observation_def: Observation definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            observation_id: Optional observation ID
            effective_datetime: Optional timestamp to use for effectiveDateTime

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

        value_type = observation_def.get("value_type") or observation_def.get("valueType")
        value_type = (value_type or "quantity").lower()

        if "value" in observation_def and value_type == "quantity":
            value = observation_def.get("value")
        else:
            value_range = observation_def.get("range", {})
            min_val = value_range.get("min", 0)
            max_val = value_range.get("max", 100)
            value = round(self.rng.uniform(min_val, max_val), 2)

        unit = observation_def.get("unit", "1") or "1"
        quantity_def = observation_def.get("valueQuantity")
        if quantity_def:
            quantity = Quantity(
                value=quantity_def.get("value", value),
                unit=quantity_def.get("unit", unit),
                system=quantity_def.get("system", "http://unitsofmeasure.org"),
                code=quantity_def.get("code", quantity_def.get("unit", unit)),
            )
        else:
            quantity = Quantity(
                value=value,
                unit=unit,
                system="http://unitsofmeasure.org",
                code=unit,
            )

        observation_kwargs: Dict[str, Any] = {
            "id": observation_id,
            "status": observation_def.get("status", RESOURCE_DEFAULTS["OBSERVATION_STATUS"]),
            "code": CodeableConcept(coding=[coding]),
            "subject": Reference(reference=patient_ref or f"Patient/{patient_id}"),
        }

        event_time = effective_datetime or (datetime.now() - timedelta(days=self.rng.randint(1, 30)))
        observation_kwargs["effectiveDateTime"] = self._format_datetime(event_time)

        if value_type in {"boolean", "flag"}:
            observation_kwargs["valueBoolean"] = bool(observation_def.get("positive", True))
        elif value_type in {"string", "text"}:
            observation_kwargs["valueString"] = observation_def.get("value", observation_def.get("display", ""))
        elif value_type in {"integer", "int"}:
            observation_kwargs["valueInteger"] = int(observation_def.get("value", value))
        elif value_type in {"codeableconcept", "coded", "code"}:
            coded_value = observation_def.get("value", {})
            if isinstance(coded_value, dict):
                observation_kwargs["valueCodeableConcept"] = CodeableConcept(
                    coding=[
                        Coding(
                            system=coded_value.get("system", SYSTEMS["LOINC"]),
                            code=coded_value.get("code", coded_value.get("value")),
                            display=coded_value.get("display"),
                        )
                    ]
                )
            else:
                observation_kwargs["valueString"] = str(coded_value)
        else:
            observation_kwargs["valueQuantity"] = quantity

        if reference_range := observation_def.get("reference_range"):
            observation_kwargs["referenceRange"] = [reference_range]

        observation = Observation(**observation_kwargs)

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

        frequency = medication_def.get("frequency", 1)
        frequency = 1 if frequency < 1 else int(frequency)

        now = datetime.now()
        status = medication_def.get("status", RESOURCE_DEFAULTS["MEDICATION_REQUEST_STATUS"])
        if medication_def.get("completed_days_ago") is not None and "status" not in medication_def:
            status = "completed"

        duration_days = medication_def.get("duration_days") or medication_def.get("durationDays")
        completed_days_ago = medication_def.get("completed_days_ago") or medication_def.get("completedDaysAgo")
        start_days_ago = medication_def.get("start_days_ago") or medication_def.get("startDaysAgo")

        if start_days_ago is not None:
            start_date = now - timedelta(days=int(start_days_ago))
        elif completed_days_ago is not None and duration_days is not None:
            start_date = now - timedelta(days=int(completed_days_ago) + int(duration_days))
        else:
            start_date = now

        if completed_days_ago is not None:
            end_date = now - timedelta(days=int(completed_days_ago))
        elif duration_days is not None:
            end_date = start_date + timedelta(days=int(duration_days))
        else:
            end_date = None

        bounds_period: Dict[str, Any] = {}
        bounds_period["start"] = self._format_datetime(start_date)
        if end_date:
            bounds_period["end"] = self._format_datetime(end_date)

        timing_repeat: Dict[str, Any] = {
            "frequency": frequency,
            "period": 1,
            "periodUnit": "d",
        }
        if bounds_period:
            timing_repeat["boundsPeriod"] = bounds_period

        dosage = Dosage(
            text=medication_def.get("sig", "Take as directed"),
            timing={"repeat": timing_repeat},
            patientInstruction=medication_def.get("instructions"),
        )

        medication_kwargs: Dict[str, Any] = {
            "id": med_request_id,
            "status": status,
            "intent": medication_def.get("intent", RESOURCE_DEFAULTS["MEDICATION_REQUEST_INTENT"]),
            "medication": CodeableReference(concept=CodeableConcept(coding=[coding])),
            "subject": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "authoredOn": self._format_datetime(start_date),
            "dosageInstruction": [dosage],
        }

        if priority := medication_def.get("priority"):
            medication_kwargs["priority"] = priority

        if reason_code := medication_def.get("reason"):
            if isinstance(reason_code, dict):
                medication_kwargs["reasonCode"] = [
                    CodeableConcept(
                        coding=[
                            Coding(
                                system=reason_code.get("system", SYSTEMS["SNOMED"]),
                                code=reason_code.get("code"),
                                display=reason_code.get("display"),
                            )
                        ]
                    )
                ]
            else:
                medication_kwargs["reasonCode"] = [CodeableConcept(text=str(reason_code))]

        notes: List[Annotation] = []
        if adherence := medication_def.get("adherence"):
            adherence_prob = adherence.get("prob")
            if adherence_prob is not None:
                notes.append(Annotation(text=f"Estimated adherence probability: {adherence_prob}"))
        if medication_def.get("notes"):
            note_text = medication_def.get("notes")
            if isinstance(note_text, list):
                notes.extend(Annotation(text=str(text)) for text in note_text)
            else:
                notes.append(Annotation(text=str(note_text)))
        if notes:
            medication_kwargs["note"] = notes

        dispense_request: Dict[str, Any] = {}
        if bounds_period:
            dispense_request["validityPeriod"] = bounds_period
        if duration_days is not None:
            dispense_request["expectedSupplyDuration"] = Duration(
                value=int(duration_days),
                unit="day",
                system="http://unitsofmeasure.org",
                code="d",
            )
        if dispense_request:
            medication_kwargs["dispenseRequest"] = dispense_request

        med_request = MedicationRequest(**medication_kwargs)

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

        # Encounter class - needs to be a CodeableConcept
        class_data = encounter_def.get("class")
        if isinstance(class_data, dict):
            class_code = class_data.get("code", RESOURCE_DEFAULTS["ENCOUNTER_CLASS_DEFAULT"])
            class_system = class_data.get("system", SYSTEMS["HL7_V3_ACTCODE"])
            class_display = class_data.get("display")
        elif class_data:
            class_code = class_data
            class_system = encounter_def.get("class_system", SYSTEMS["HL7_V3_ACTCODE"])
            class_display = encounter_def.get("class_display", "ambulatory")
        else:
            class_code = RESOURCE_DEFAULTS["ENCOUNTER_CLASS_DEFAULT"]
            class_system = SYSTEMS["HL7_V3_ACTCODE"]
            class_display = "ambulatory"

        encounter_class = CodeableConcept(
            coding=[
                Coding(
                    system=class_system,
                    code=class_code,
                    display=class_display,
                )
            ]
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
        duration_hours = encounter_def.get(
            "duration_hours",
            encounter_def.get("durationHours", RESOURCE_DEFAULTS["ENCOUNTER_DURATION_HOURS_DEFAULT"]),
        )
        end_time = start_time + timedelta(hours=duration_hours)

        period = Period(
            start=start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            end=end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        )

        # Build encounter kwargs
        kwargs = {
            "id": encounter_id,
            "status": encounter_def.get("status", RESOURCE_DEFAULTS["ENCOUNTER_STATUS"]),
            "class_fhir": [encounter_class],  # class_fhir is a list
            "type": [encounter_type],
            "subject": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "actualPeriod": period  # Changed from 'period' to 'actualPeriod'
        }

        # Add optional reason codes
        if reason := encounter_def.get("reason"):
            if isinstance(reason, str):
                reason_concept = CodeableConcept(
                    text=reason
                )
            else:
                reason_concept = CodeableConcept(
                    coding=[Coding(
                        system=reason.get("system", "http://snomed.info/sct"),
                        code=reason.get("code"),
                        display=reason.get("display")
                    )]
                )
            from fhir.resources.encounter import EncounterReason
            kwargs["reason"] = [EncounterReason(use=[reason_concept])]

        # Add performer/participant if specified
        if performer := encounter_def.get("performer"):
            from fhir.resources.encounter import EncounterParticipant
            participant = EncounterParticipant(
                actor=Reference(reference=performer)
            )
            kwargs["participant"] = [participant]

        # Add service provider (organization)
        if service_provider := encounter_def.get("serviceProvider"):
            kwargs["serviceProvider"] = Reference(reference=service_provider)

        # Create encounter
        encounter = Encounter(**kwargs)

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

    def create_immunization(
        self,
        patient_id: str,
        immunization_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        immunization_id: Optional[str] = None
    ) -> Immunization:
        """Create an Immunization resource.

        Args:
            patient_id: Patient ID reference
            immunization_def: Immunization definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            immunization_id: Optional Immunization ID

        Returns:
            Immunization resource
        """
        immunization_id = immunization_id or self.rng.uuid()

        # Extract vaccine code (CVX or other coding system)
        vaccine_data = immunization_def.get("vaccine", {})
        vaccine_coding = Coding(
            system=vaccine_data.get("system", "http://hl7.org/fhir/sid/cvx"),
            code=vaccine_data.get("code"),
            display=vaccine_data.get("display")
        )

        # Status - default to completed
        status = immunization_def.get("status", "completed")

        # Occurrence date
        days_ago = immunization_def.get("days_ago", self.rng.randint(30, 365))
        occurrence_date = datetime.now() - timedelta(days=days_ago)

        # Build the Immunization resource
        kwargs = {
            "id": immunization_id,
            "status": status,
            "vaccineCode": CodeableConcept(coding=[vaccine_coding]),
            "patient": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "occurrenceDateTime": occurrence_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        }

        # Add optional fields
        if dose_number := immunization_def.get("doseNumber"):
            kwargs["doseQuantity"] = Quantity(value=dose_number)

        if lot_number := immunization_def.get("lotNumber"):
            kwargs["lotNumber"] = lot_number

        if site := immunization_def.get("site"):
            site_coding = Coding(
                system="http://terminology.hl7.org/CodeSystem/v3-ActSite",
                code=site.get("code") if isinstance(site, dict) else site,
                display=site.get("display") if isinstance(site, dict) else None
            )
            kwargs["site"] = CodeableConcept(coding=[site_coding])

        if route := immunization_def.get("route"):
            route_coding = Coding(
                system="http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                code=route.get("code") if isinstance(route, dict) else route,
                display=route.get("display") if isinstance(route, dict) else None
            )
            kwargs["route"] = CodeableConcept(coding=[route_coding])

        if performer := immunization_def.get("performer"):
            from fhir.resources.immunization import ImmunizationPerformer
            kwargs["performer"] = [ImmunizationPerformer(actor=Reference(reference=performer))]

        if not_given := immunization_def.get("notGiven"):
            kwargs["primarySource"] = not not_given  # If not given, primarySource is False

        immunization = Immunization(**kwargs)

        return immunization

    def create_coverage(
        self,
        patient_id: str,
        coverage_def: Dict[str, Any],
        patient_ref: Optional[str] = None,
        coverage_id: Optional[str] = None
    ) -> Coverage:
        """Create a Coverage resource.

        Args:
            patient_id: Patient ID reference
            coverage_def: Coverage definition
            patient_ref: Optional custom patient reference (defaults to Patient/{patient_id})
            coverage_id: Optional Coverage ID

        Returns:
            Coverage resource
        """
        coverage_id = coverage_id or self.rng.uuid()

        # Status - default to active
        status = coverage_def.get("status", "active")

        # Type of coverage
        type_data = coverage_def.get("type", {})
        if type_data:
            type_coding = Coding(
                system=type_data.get("system", "http://terminology.hl7.org/CodeSystem/v3-ActCode"),
                code=type_data.get("code", "EHCPOL"),
                display=type_data.get("display", "Extended healthcare")
            )
            coverage_type = CodeableConcept(coding=[type_coding])
        else:
            # Default to general health insurance
            coverage_type = CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    code="EHCPOL",
                    display="Extended healthcare"
                )]
            )

        # Build the Coverage resource
        kwargs = {
            "id": coverage_id,
            "status": status,
            "beneficiary": Reference(reference=patient_ref or f"Patient/{patient_id}"),
            "kind": coverage_def.get("kind", "insurance")  # Required field
        }

        # Add type if provided (optional in some FHIR versions)
        if type_data:
            kwargs["type"] = coverage_type

        # Add subscriber if provided
        if subscriber := coverage_def.get("subscriber"):
            kwargs["subscriber"] = Reference(reference=subscriber)
        else:
            # Default to beneficiary as subscriber
            kwargs["subscriber"] = Reference(reference=patient_ref or f"Patient/{patient_id}")

        # Add paymentBy (insurance company) - Note: FHIR R5 uses paymentBy instead of payor
        from fhir.resources.coverage import CoveragePaymentBy

        if payor := coverage_def.get("payor"):
            if isinstance(payor, str):
                kwargs["paymentBy"] = [CoveragePaymentBy(party=Reference(reference=payor))]
            elif isinstance(payor, list):
                kwargs["paymentBy"] = [CoveragePaymentBy(party=Reference(reference=p)) for p in payor]
            else:
                kwargs["paymentBy"] = [CoveragePaymentBy(party=Reference(reference=payor.get("reference")))]
        else:
            # Default payor
            kwargs["paymentBy"] = [CoveragePaymentBy(party=Reference(reference="Organization/default-insurance"))]

        # Add period if specified
        if period := coverage_def.get("period"):
            start_date = None
            end_date = None

            if start_days_ago := period.get("start_days_ago"):
                start_date = (datetime.now() - timedelta(days=start_days_ago)).strftime("%Y-%m-%d")
            elif start := period.get("start"):
                start_date = start

            if end_days_ago := period.get("end_days_ago"):
                end_date = (datetime.now() - timedelta(days=end_days_ago)).strftime("%Y-%m-%d")
            elif end := period.get("end"):
                end_date = end

            if start_date or end_date:
                kwargs["period"] = Period(start=start_date, end=end_date)

        # Add identifier if provided
        if identifier := coverage_def.get("identifier"):
            kwargs["identifier"] = [
                Identifier(
                    system=identifier.get("system", "http://example.org/insurance-id"),
                    value=identifier.get("value")
                )
            ]

        # Add relationship if provided
        if relationship := coverage_def.get("relationship"):
            rel_coding = Coding(
                system="http://terminology.hl7.org/CodeSystem/subscriber-relationship",
                code=relationship if isinstance(relationship, str) else relationship.get("code"),
                display=relationship.get("display") if isinstance(relationship, dict) else None
            )
            kwargs["relationship"] = CodeableConcept(coding=[rel_coding])

        coverage = Coverage(**kwargs)

        return coverage