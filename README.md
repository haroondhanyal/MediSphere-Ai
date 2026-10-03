# MediSphere AI

![MediSphere AI logo](./public/medisphere-logo.svg)

AI-native unified healthcare workspace for local care coordination and administration workflows.

## Project status

Implementation phases 1–7 have a working local application slice. Each phase and the remaining production integrations are described in the [delivery roadmap](docs/roadmap.md).

| Phase | Included in this repository |
|---|---|
| 1 · Foundation | Next.js app, FastAPI service, SQLAlchemy database, tenant-aware authentication, seeded role permissions, audit events, Docker Compose |
| 2 · Care workflows | Patient records, practitioners, appointment scheduling, encounter notes |
| 3 · Clinical orders | Prescriptions, lab orders and results, radiology orders and reports |
| 4 · Communications | Telehealth session coordination, organization messages, notification center |
| 5 · Revenue cycle | Insurance policies, claims, prior authorizations, invoices and manual payments, pharmacy dispensing queue |
| 6 · Copilot | Permission-aware retrieval for patients, appointments, prescriptions, claims, and organization totals; see [Copilot details](docs/copilot.md) |
| 7 · Interoperability | FHIR R4 Patient create/read/search; Practitioner, Appointment, and Encounter read/search; CapabilityStatement; see [FHIR details](docs/fhir.md) |

The phases are complete as local, permission-checked workflow slices. The app does not claim connected video calls, live push delivery, external payer/payment processing, wearable feeds, generative clinical AI, SMART-on-FHIR OAuth, or full FHIR conformance. Those require external services, credentials, privacy review, or additional implementation; they are tracked in the roadmap.

## Run locally

Start PostgreSQL and the API:

```sh
docker compose up --build
```

In another terminal, start the web app:

```sh
npm install
npm run dev
```

Open <http://localhost:3000>. The API is available at <http://localhost:8000>, and its OpenAPI page is <http://localhost:8000/docs>.

The local seed creates organization `medisphere-health` and demo accounts `superadmin@medisphere.local`, `admin@medisphere.local`, `doctor@medisphere.local`, `nurse@medisphere.local`, `patient@medisphere.local`, `insurance@medisphere.local`, `pharmacy@medisphere.local`, and `lab@medisphere.local`. The local demo password is `MediSphere-Demo-2026!`. These credentials are for local development only. Set unique `JWT_SECRET` and `SEED_ADMIN_PASSWORD` values outside local development. Node.js 20.9 or newer is recommended.

## Screens and code layout

Each workspace route has its own folder under `src/app/(workspace)/<screen>/`. Feature UI lives in `src/features/`, shared layout components in `src/components/`, and route/navigation metadata in `src/lib/modules.ts`. The logo is at [public/medisphere-logo.svg](public/medisphere-logo.svg); the browser tab icon is [public/medisphere-mark.svg](public/medisphere-mark.svg).

The frontend calls the FastAPI service through same-origin route handlers under `src/app/api/`. The API lives in `apps/api/app/`; schema changes are managed by Alembic migrations in `apps/api/migrations/versions/`. API routes use organization scoping and domain permissions. Audit views and copilot lookups are also organization scoped.

## Configuration and verification

Copy `.env.example` when configuring the API environment. For production, provide a strong JWT secret, secure cookies behind HTTPS, a production database, and a non-demo seed password. Do not deploy the bundled demo credentials.

Run frontend checks:

```sh
npm run lint
npm run build
```

Run API tests:

```sh
python -m pip install -r apps/api/requirements-dev.txt
cd apps/api
pytest
```

The FHIR endpoints use the authenticated MediSphere session and return `application/fhir+json`. Supported resources and search parameters are documented in [docs/fhir.md](docs/fhir.md).
