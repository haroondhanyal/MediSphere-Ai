# Resume project entry

Use this as a project entry in a resume or portfolio. Replace the role and dates with your own details, and keep only the contributions you personally completed.

## MediSphere AI — Unified Healthcare Workspace

**Role:** [Your role] · **Dates:** [Month Year – Month Year] · **Stack:** Next.js, React, TypeScript, FastAPI, Python, SQLAlchemy, Alembic, PostgreSQL, Docker, GitHub Actions, Playwright, k6, Kubernetes, Terraform

- Built a multi-organization healthcare workspace with role-based access for administrators, clinicians, nurses, patients, pharmacy, laboratory, and insurance workflows.
- Implemented patient and practitioner records, scheduling, encounter documentation, prescriptions, lab and radiology orders, team communications, claims, authorizations, invoicing, and audit history.
- Added an initial FHIR R4 API slice for Patient, Practitioner, Appointment, and Encounter resources, with a CapabilityStatement.
- Developed remote-monitoring ingestion using per-device bearer credentials, configurable organization thresholds, alert review, and token rotation.
- Added API workflow coverage, a Playwright sign-in journey, an authenticated k6 scenario, health probes, Prometheus metrics, and Kubernetes/Terraform deployment baselines.
- Verified locally with 18 passing API tests, a passing browser journey, frontend lint/build checks, and fresh Alembic migrations.

**Scope:** The project includes local workflow and deployment baselines. It has not been deployed to a production cluster; provider-specific wearable, video, payer, and payment integrations require external services and credentials.
