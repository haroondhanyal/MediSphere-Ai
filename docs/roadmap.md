# MediSphere AI delivery phases

The project is divided into the 10 implementation phases from the product brief. Complete and verify one phase before expanding into the next.

| Phase | Scope | Status |
|---|---|---|
| 1 | Monorepo foundation, authentication, RBAC, database, base UI | Complete |
| 2 | Patients, practitioners, appointments, EHR encounters | Complete |
| 3 | Clinical documentation, prescriptions, lab, radiology | Complete |
| 4 | Telehealth session coordination, chat, notifications | Complete local workflow slice: session lifecycle, secure messaging, notification center. A video provider and push delivery can be configured as later integrations |
| 5 | Insurance, claims, prior authorization, billing | Complete local workflow slice: coverage, claim and authorization status, invoices/payments, pharmacy dispensing queue. Payer and payment gateway connections remain later integrations |
| 6 | AI copilot, retrieval, patient assistant | Complete private retrieval slice: permission-aware patient, appointment, prescription, claim, and aggregate lookup with audited use. It does not generate clinical advice or require an external model |
| 7 | FHIR interoperability | Complete initial R4 slice: Patient create/read/search and Practitioner, Appointment, and Encounter read/search, plus CapabilityStatement. Profile validation, terminology, OAuth/SMART, and additional resources remain later conformance work |
| 8 | Remote monitoring | Partial; manual device and reading capture exists, wearable feeds and clinical alerting pending |
| 9 | Automation and performance testing | Partial; API integration tests and k6 smoke scenario exist, browser and load suites pending |
| 10 | Docker, CI/CD, observability, Kubernetes, Terraform | Partial; local Docker Compose and GitHub CI exist, production observability/deployment pending |

“Complete” means the local phase workflow slice exists and is permission checked. Production integrations such as external identity providers, pharmacy networks, diagnostic devices, payment gateways, video providers, and jurisdiction-specific clinical review still need their own implementation and credentials.
