# Fintech Margin & Reconciliation Intelligence Engine

Deterministic reconciliation + AI-assisted investigation for African payment rail
economics (Paystack, Flutterwave, NIP bank transfer). Answers one question:
**are we getting the fee economics we're actually contracted for?**

All data is synthetic. Rate cards in `/rate-cards` are grounded in publicly
documented 2026 pricing (sources cited in each file) — no live provider
integration, no real customer data, no real funds.

## Why this exists

Global reconciliation tooling (Optimus, Rexi, card-network fee validators) is
built around card-network interchange for US/EU rails. Nothing serves NIP /
Paystack / Flutterwave-style economics. This is a working demonstration of
that gap, built end-to-end with the security and DevSecOps practices a
production fintech system would need.

## Structure

- `rate-cards/` — versioned provider pricing configs (source of truth for expected fees)
- `reconciliation-engine/` — deterministic expected-vs-actual fee calculation
- `ai-investigator/` — evidence-only LLM explanation layer (no tool calls, schema-validated output)
- `api/` — ingestion + case management endpoints
- `app/` — UI (economics overview, exception queue, partner simulator)
- `docs/` — architecture, threat model, security controls, incident response
- `.github/workflows/` — CI/CD security pipeline (SAST, dependency scan, secret scan, SBOM)

## Status

Day 1 of 12: rate cards grounded, scaffold in place. See `docs/architecture.md`
for the build plan.
