# MediSphere AI

![MediSphere AI logo](./public/medisphere-logo.svg)

**MediSphere AI is a unified healthcare operations workspace.** It brings patient administration, clinical coordination, revenue workflows, remote monitoring, and organization settings into one multi-organization web application. A care team can follow work from registration and scheduling through clinical orders, communication, and billing while access is checked against the user's organization and role.

This repository contains a local product implementation and deployment baseline. Its sample dashboard figures are illustrative; local seed patient records are synthetic. It is not a production clinical system and does not connect to real payer, payment, video, or wearable providers by default.

## Product tour

The screenshots below were captured from the running application at desktop size. The seeded patient directory contains synthetic demo data. The overview cards are labeled sample workspace data in the UI.

| Sign in | Workspace overview |
|---|---|
| ![MediSphere AI sign-in screen](./docs/screenshots/01-sign-in.png) | ![MediSphere AI workspace overview](./docs/screenshots/02-dashboard.png) |

| Patient directory | Care team profiles |
|---|---|
| ![Patient directory screen](./docs/screenshots/03-patients.png) | ![Care team screen with practitioner profiles](./docs/screenshots/04-care-team.png) |

| Appointment scheduling | Remote monitoring |
|---|---|
| ![Appointment scheduling screen](./docs/screenshots/05-appointments.png) | ![Remote patient monitoring screen](./docs/screenshots/06-remote-monitoring.png) |

| Organization profile and settings | Care copilot |
|---|---|
| ![Organization profile settings screen](./docs/screenshots/07-organization-settings.png) | ![Care copilot screen](./docs/screenshots/08-copilot.png) |

The remaining workflow screenshots cover all other workspace modules:

### Clinical workflow screens

| Encounters | Prescriptions |
|---|---|
| ![Encounter documentation screen](./docs/screenshots/09-encounters.png) | ![Prescription workflow screen](./docs/screenshots/10-prescriptions.png) |

| Laboratory | Radiology |
|---|---|
| ![Laboratory orders and results screen](./docs/screenshots/11-laboratory.png) | ![Radiology workflow screen](./docs/screenshots/12-radiology.png) |

| Pharmacy | Telehealth |
|---|---|
| ![Pharmacy dispensing screen](./docs/screenshots/13-pharmacy.png) | ![Telehealth coordination screen](./docs/screenshots/14-telehealth.png) |

### Administration and revenue screens

| Team messages | Notifications |
|---|---|
| ![Organization messages screen](./docs/screenshots/15-messages.png) | ![Notifications screen](./docs/screenshots/16-notifications.png) |

| Insurance | Claims |
|---|---|
| ![Insurance coverage screen](./docs/screenshots/17-insurance.png) | ![Claims workflow screen](./docs/screenshots/18-claims.png) |

| Prior authorization | Billing |
|---|---|
| ![Prior authorization workflow screen](./docs/screenshots/19-authorizations.png) | ![Billing and payments screen](./docs/screenshots/20-billing.png) |

### Reporting and governance screens

| Analytics | Audit log |
|---|---|
| ![Analytics screen](./docs/screenshots/21-analytics.png) | ![Audit log screen](./docs/screenshots/22-audit-log.png) |

## What the product does

### Care delivery

- **Patients:** maintain organization-scoped patient records with MRN, name, contact details, demographics, and active status.
- **Care team:** add one or several practitioner profiles in a single save. Profiles include role, specialty, work email, contact number, and active status.
- **Appointments and encounters:** coordinate a visit with a patient and practitioner, then record an encounter and its clinical note.
- **Prescriptions and pharmacy:** create medication orders and follow their dispensing workflow.
- **Laboratory and radiology:** create orders, track status, and record results or reports.
- **Telehealth:** coordinate virtual visit sessions and their local lifecycle. A video provider is not connected by default.

### Team operations and revenue

- **Messages and notifications:** organize internal team conversations and in-app operational notifications.
- **Insurance and claims:** record insurance coverage and manage claim status.
- **Prior authorization:** create requests and track payer decisions.
- **Billing:** create invoices and record manual payments. Payment gateway processing is not included.
- **Analytics:** review organization-level workflow summaries.
- **Audit log:** inspect recorded access and workflow activity.

### Monitoring and record retrieval

- **Remote monitoring:** register a patient device, issue a one-time device bearer token, ingest timestamped readings, configure organization thresholds, and review or acknowledge alerts. Threshold alerts are signals for a clinician to review; they are not diagnoses.
- **Care copilot:** retrieve records and summaries that the signed-in role is permitted to see, including patients, appointments, prescriptions, claims, and organization totals. It is a permission-aware search workflow; it does not generate diagnoses or treatment recommendations.
- **FHIR R4:** expose the implemented Patient create/read/search operations and Practitioner, Appointment, and Encounter read/search operations, plus a CapabilityStatement. See the [FHIR guide](docs/fhir.md) for supported interactions and limits.

### Organization profile

Workspace settings include the organization name, logo URL, contact number, timezone, default language, and subscription details. The configured logo appears in the workspace switcher. Logo images are referenced by URL; image upload and storage are not part of this local slice.

## Workflows at a glance

```mermaid
flowchart LR
  registration[Patient registration] --> scheduling[Appointment scheduling]
  team[Care team profiles] --> scheduling
  scheduling --> encounter[Encounter documentation]
  encounter --> orders[Prescription, lab, and imaging orders]
  orders --> followup[Pharmacy and results follow-up]
  device[Patient monitoring device] --> readings[Reading ingestion]
  readings --> thresholds[Configured threshold review]
  insurance[Coverage and authorization] --> claims[Claims and billing]
  claims --> audit[Audit history]
  encounter --> audit
```

## Product areas

| Area | Screens | Purpose |
|---|---|---|
| Workspace | Overview, Settings | Navigate the product and manage organization profile details |
| Care delivery | Patients, Care team, Appointments, Encounters | Keep patient, practitioner, scheduling, and visit information together |
| Clinical operations | Prescriptions, Laboratory, Radiology, Pharmacy, Telehealth | Coordinate orders, results, dispensing, and virtual-visit status |
| Administration | Messages, Notifications, Insurance, Claims, Prior authorization, Billing | Handle team communication and revenue-cycle work |
| Insights | Analytics, Care copilot, Audit log | Summarize workflows, retrieve allowed records, and review activity |
| Monitoring | Remote monitoring | Enroll devices, receive readings, and review threshold alerts |

## Access and data boundaries

- Users authenticate with an HTTP-only session cookie. The API checks organization membership and domain permissions on each protected workflow.
- Records and retrieval queries are scoped to the active organization. The navigation UI is not an access-control boundary; API permission checks enforce access.
- Workflow actions write audit events. Device ingestion uses scoped per-device credentials that can be rotated.
- Local demo accounts and synthetic seed records are for development only. Production startup does not seed the bundled demo users or patient data.
- Healthcare privacy, security, retention, and jurisdiction-specific compliance reviews are deployment responsibilities. This repository is not a compliance certification.
- Users can create a separate workspace during signup with one of four roles. Password recovery uses a one-time expiring link; local development displays the link, while production sends it through the configured SMTP relay.

## Technology and architecture

| Layer | Implementation |
|---|---|
| Web application | Next.js 16, React 19, TypeScript, Lucide |
| API | FastAPI, Pydantic, SQLAlchemy 2 |
| Database | PostgreSQL 16 for Compose; SQLite for isolated API tests and local utilities |
| Schema changes | Alembic migrations |
| Web-to-API path | Same-origin Next.js route handlers proxy to FastAPI |
| Delivery baseline | Docker Compose, GitHub Actions, Playwright, k6, Kubernetes manifests, Terraform |
| Operations | Health endpoints, structured request logs, Prometheus-compatible `/metrics` endpoint |

```mermaid
flowchart LR
  browser[Browser] --> web[Next.js web app]
  web -->|same-origin API proxy and session cookie| api[FastAPI]
  api --> db[(PostgreSQL)]
  device[Authorized device] -->|scoped bearer token| api
  prometheus[Prometheus] -->|scrape /metrics| api
```

The API is organized under `/api/v1/`. Main workflow groups include `/auth`, `/patients`, `/practitioners`, `/appointments`, `/encounters`, `/remote-monitoring`, and `/fhir/r4`. During local development, FastAPI's OpenAPI page is available at `/docs`.

## Run locally

Start the full stack (web, API, and PostgreSQL):

```sh
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000/login` to sign in. Use **Create an account** to create a separate workspace, choose a role, and optionally add a profile photo. Local forgot-password requests show a one-time reset link in the browser; production email delivery requires the SMTP settings listed in the [deployment guide](docs/deployment.md).

Open <http://localhost:3000>. The API is available at <http://localhost:8000>, and interactive API documentation is at <http://localhost:8000/docs>.

To run only the web process on the host while the database and API run in Compose:

```sh
docker compose up -d db api
npm install
npm run dev
```

The local seed creates organization `medisphere-health`, 15 synthetic patient profiles, and demo role accounts. All listed accounts use the local-only password `MediSphere-Demo-2026!`.

| Role | Login email |
|---|---|
| Super administrator | `superadmin@medisphere.local` |
| Hospital administrator | `admin@medisphere.local` |
| Doctor | `doctor@medisphere.local` |
| Nurse | `nurse@medisphere.local` |
| Insurance reviewer | `insurance@medisphere.local` |
| Pharmacist | `pharmacy@medisphere.local` |
| Lab technician | `lab@medisphere.local` |

These credentials and synthetic patient records are strictly for local development. Patient profiles are records, not individual portal accounts; the old `patient@medisphere.local` demo login is disabled. Production containers do not seed demo users or patient data. Follow the [deployment guide](docs/deployment.md) to provision an initial administrator. Node.js 20.9 or newer is recommended.

## Repository map

| Path | Contents |
|---|---|
| `src/app/(workspace)/` | Route entry points for each authenticated screen |
| `src/features/` | Workspace-specific user interfaces and client workflows |
| `src/components/` | Shared application shell, sign-in, and page components |
| `src/app/api/` | Same-origin route handlers that proxy requests to FastAPI |
| `apps/api/app/` | API routes, data models, validation schemas, auth, and seed data |
| `apps/api/migrations/versions/` | Alembic schema history |
| `docs/` | Product, interoperability, deployment, roadmap, and screenshot documentation |
| `e2e/`, `apps/api/tests/` | Browser and API workflow coverage |
| `deploy/`, `observability/` | Kubernetes/Terraform and monitoring examples |

## Developer commands

Frontend lint and production build:

```sh
npm run lint
npm run build
```

API test suite:

```sh
python -m pip install -r apps/api/requirements-dev.txt
cd apps/api
pytest
```

Browser flow (requires the local stack and Chromium):

```sh
npx playwright install chromium
npm run test:e2e
```

Authenticated k6 smoke scenario:

```sh
docker compose up -d db api
docker compose --profile performance run --rm k6
```

## Delivery scope and next integrations

The repository implements local workflow slices and deployment scaffolding across ten project phases. Production operation still requires a real cluster, managed database, secrets, TLS, monitoring installation, and privacy review. External video, payer, payment, and wearable connectors need selected providers and credentials. SMART-on-FHIR OAuth, broader resource coverage, and jurisdiction-specific FHIR conformance are also outside the current slice.

See the [delivery roadmap](docs/roadmap.md), [deployment guide](docs/deployment.md), and [FHIR guide](docs/fhir.md) for specific coverage and setup details. The [project resume entry](docs/project-resume-entry.md) is a summary of the project; replace its role and dates with your own before using it.
