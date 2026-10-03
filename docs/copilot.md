# Care Copilot

The Care Copilot provides private, permission-aware retrieval over existing organization records. It currently supports patient lookup, recent appointments, prescriptions, claims, and a compact operations summary. Results stay in the MediSphere API and each request writes an audit event without recording the user's query text.

The copilot is intentionally factual. It does not use an external model, diagnose conditions, recommend treatment, or act on records. Each query type checks the same domain permission used by the corresponding workflow. Results are capped at 20 records and omit patient contact details.

The current intent router is keyword based. A later generative assistant should be separately evaluated for privacy, clinical safety, and provider configuration before it can receive patient data.
