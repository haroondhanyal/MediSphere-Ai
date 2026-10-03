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
| 8 | Remote monitoring | Complete local workflow: device registration, one-time per-device credentials, authenticated remote reading intake, configurable per-organization thresholds, alert review and acknowledgement |
| 9 | Automation and performance testing | Complete baseline: API workflow tests, Playwright browser journey, authenticated k6 load smoke, and GitHub Actions jobs |
| 10 | Docker, CI/CD, observability, Kubernetes, Terraform | Complete deployment baseline: production containers, health checks, request telemetry, Prometheus rules, Kubernetes resources, Terraform for an existing cluster |

“Complete” means the documented local workflow or delivery baseline is implemented. Provider-specific wearable, pharmacy, payer, payment and video integrations need the chosen vendor and credentials. Production rollout also needs a managed database, cluster access, secret provisioning, DNS/TLS, and privacy/security review.
