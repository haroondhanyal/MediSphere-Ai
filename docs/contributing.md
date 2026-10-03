# Working in parallel

## Suggested ownership for 7–8 developers

1. Platform owner: app shell, shared components, integration.
2. Patient and practitioner portals.
3. Appointments and telehealth.
4. EHR and clinical encounters.
5. Labs, radiology, and pharmacy.
6. Billing, insurance, and claims.
7. Analytics, reports, and audit.
8. Auth, organizations, and settings.

## Keep changes easy to integrate

- Route pages compose module screens; keep feature logic in src/features/<module>/.
- Keep module-specific types and components beside their feature.
- Promote a component to src/components/ when multiple modules need it.
- Assign one owner to src/lib/modules.ts and the app shell to prevent merge conflicts.
- Agree on shared component props before other modules depend on them.
- Do not add visual-only behavior for security-sensitive workflows.

## Routes

/dashboard, /patients, /doctors, /appointments, /encounters, /prescriptions, /labs, /radiology, /pharmacy, /telehealth, /insurance, /claims, /billing, /analytics, /audit, and /settings.
