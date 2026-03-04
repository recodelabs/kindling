"""Configuration constants for Kindling."""

from typing import Dict, List

# Default system URLs
SYSTEMS = {
    "MRN": "http://hospital.example/mrn",
    "SNOMED": "http://snomed.info/sct",
    "LOINC": "http://loinc.org",
    "RXNORM": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "HL7_CONDITION_CLINICAL": "http://terminology.hl7.org/CodeSystem/condition-clinical",
    "HL7_CONDITION_VER_STATUS": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
    "HL7_V3_ACTCODE": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
    "UNITS": "http://unitsofmeasure.org"
}

# Default demographics data
DEMOGRAPHICS = {
    "MALE_NAMES": [
        "John", "David", "Michael", "Robert", "William",
        "James", "Joseph", "Charles", "Thomas", "Christopher"
    ],
    "FEMALE_NAMES": [
        "Mary", "Linda", "Sarah", "Emma", "Jennifer",
        "Patricia", "Elizabeth", "Susan", "Jessica", "Margaret"
    ],
    "FAMILY_NAMES": [
        "Smith", "Johnson", "Brown", "Jones", "Miller",
        "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez"
    ],
    "DEFAULT_AGE_MIN": 18,
    "DEFAULT_AGE_MAX": 90
}

# Default address data
DEFAULT_ADDRESS = {
    "LINE": ["123 Main Street"],
    "CITY": "Boston",
    "STATE": "MA",
    "POSTAL_CODE": "02134",
    "COUNTRY": "US"
}

# Default telecom data
DEFAULT_TELECOM = [
    {
        "system": "phone",
        "value": "555-1234",
        "use": "home"
    },
    {
        "system": "email",
        "value": "patient@example.com",
        "use": "home"
    }
]

# Medical codes for testing/validation
TEST_CODES = {
    "DIABETES_SNOMED": "44054006",
    "HYPERTENSION_SNOMED": "38341003",
    "ASTHMA_SNOMED": "195967001",
    "HBA1C_LOINC": "4548-4",
    "GLUCOSE_LOINC": "2339-0",
    "BP_LOINC": "85354-9",
    "METFORMIN_RXNORM": "860975",
    "LISINOPRIL_RXNORM": "29046",
    "ALBUTEROL_RXNORM": "435"
}

# Observation category system
OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"

# LOINC codes that are vital signs (per FHIR vital-signs profile)
VITAL_SIGNS_LOINC = {
    "85354-9",   # Blood pressure panel
    "8480-6",    # Systolic blood pressure
    "8462-4",    # Diastolic blood pressure
    "8867-4",    # Heart rate
    "9279-1",    # Respiratory rate
    "8310-5",    # Body temperature
    "2708-6",    # SpO2
    "39156-5",   # BMI
    "29463-7",   # Body weight
    "8302-2",    # Body height
    "8287-5",    # Head circumference
    "3141-9",    # Body weight (measured)
    "59408-5",   # SpO2 by pulse oximetry
    "8478-0",    # Mean blood pressure
}

# Default values for resources
RESOURCE_DEFAULTS = {
    "CONDITION_CLINICAL_STATUS": "active",
    "CONDITION_VERIFICATION_STATUS": "confirmed",
    "OBSERVATION_STATUS": "final",
    "MEDICATION_REQUEST_STATUS": "active",
    "MEDICATION_REQUEST_INTENT": "order",
    "ENCOUNTER_STATUS": "finished",
    "ENCOUNTER_CLASS_DEFAULT": "AMB",
    "ENCOUNTER_DURATION_HOURS_DEFAULT": 1
}