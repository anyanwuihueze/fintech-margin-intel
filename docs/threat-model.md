# Threat Model

## Assets
- Rate card data (integrity of expected-fee calculation depends on it)
- Transaction/settlement records (synthetic, but modeled on real structure)
- Audit log (must be tamper-evident)
- AI investigator inputs/outputs (must not be able to trigger actions)

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Rate card silently edited after transactions were reconciled against it | Rate cards are versioned and immutable once published; reconciliation always references the version active at transaction time |
| Forged or replayed transaction/settlement events | Not applicable in v1 — synthetic data generator only, no external ingestion in scope. Revisit if provider-integration phase is added later |
| Audit log tampering | Hash-chained entries, insert-only DB role for the audit table, no update/delete grants |
| Prompt injection via transaction memo/narration fields reaching the AI investigator | Memo fields passed as delimited, clearly-untrusted data; investigator output is schema-validated; investigator has no tool-calling ability and cannot trigger Hold/Escalate/Close actions directly — a human always confirms |
| AI investigator hallucinating a fee amount, transaction, or evidence item | Investigator prompt restricts it to the supplied evidence bundle only; deterministic engine computes all figures; output schema requires evidence IDs for every claim |
| Secrets leaking into the repo | gitleaks in CI on every push |
| Vulnerable dependencies | pip-audit / npm audit + Trivy container scan in CI |
| Unauthorized access to case data | Two roles (analyst, admin); analysts cannot modify rate cards |

## Out of scope for this build
- Real provider API integration
- Multi-tenant isolation
- Production-grade key management (KMS) — env vars + gitleaks only, noted as a known limitation
