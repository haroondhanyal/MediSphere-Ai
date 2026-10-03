# FHIR interoperability

The current interoperability slice implements FHIR R4 resources at `/api/v1/fhir/r4`:

| Resource | Supported interactions | Search parameters |
|---|---|---|
| Patient | create, read, search | `name` |
| Practitioner | read, search | `name` |
| Appointment | read, search | `patient` (Patient reference) |
| Encounter | read, search | `patient` (Patient reference) |

`GET /api/v1/fhir/r4/metadata` returns the server CapabilityStatement. Responses use `application/fhir+json`; search returns a Bundle with type `searchset`. Routes are tenant scoped, require the matching application permission, and write access events to the audit log.

Patient mapping covers MRN identifier, official name, active state, administrative gender, birth date, phone, and email. Practitioner, Appointment, and Encounter mappings cover the local identity, schedule, participant, and note fields available in the database. The CapabilityStatement advertises the interactions above. Profile validation, terminology binding, SMART-on-FHIR/OAuth scopes, bulk data, write interactions for other resource types, and additional resources remain future conformance work.

The resource shape follows the normative FHIR R4 Patient and Bundle structures. See [HL7 FHIR R4 Patient](https://hl7.org/fhir/R4/patient.html) and [HL7 FHIR R4 Bundle](https://hl7.org/fhir/R4/bundle.html).
