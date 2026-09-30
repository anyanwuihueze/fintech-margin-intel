"""
Day 6 — integrated reconciliation workflow.

Wires transaction + settlement -> compute_variance (deterministic engine,
sole source of financial truth) -> exception creation for flagged results
-> every step logged to the hash-chained audit trail.

No AI. No PWA. This module orchestrates calls into engine.py, exceptions.py
and audit.py — it introduces no new financial logic of its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from models import Transaction, SettlementRecord
from engine import compute_variance
from exceptions import create_exception_case, ExceptionCase
from audit import AuditLog
from rate_card_loader import RateCardStore


@dataclass
class ReconciliationBatchResult:
    batch_id: str
    total_cases: int
    flagged_count: int
    clean_count: int
    exceptions: List[ExceptionCase] = field(default_factory=list)
    audit_log: AuditLog = field(default_factory=AuditLog)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_reconciliation_batch(
    pairs: List[Tuple[Transaction, SettlementRecord]],
    batch_id: str,
    store: Optional[RateCardStore] = None,
) -> ReconciliationBatchResult:
    if store is None:
        store = RateCardStore()

    log = AuditLog()
    exceptions: List[ExceptionCase] = []
    flagged_count = 0

    log.append(
        event_id=f"AUD-{batch_id}-START",
        event_type="reconciliation.started",
        actor="system",
        payload={"batch_id": batch_id, "total_pairs": len(pairs)},
        timestamp=_now_iso(),
    )

    for transaction, settlement in pairs:
        result = compute_variance(
            transaction,
            actual_fee_ngn=settlement.actual_fee_ngn,
            store=store,
        )

        log.append(
            event_id=f"AUD-{transaction.transaction_id}-RECON",
            event_type="reconciliation.result",
            actor="reconciliation-engine",
            payload={
                "transaction_id": result.transaction_id,
                "expected_fee_ngn": str(result.expected_fee_ngn),
                "actual_fee_ngn": str(result.actual_fee_ngn),
                "variance_ngn": str(result.variance_ngn),
                "flagged": result.flagged,
            },
            timestamp=_now_iso(),
        )

        if result.flagged:
            flagged_count += 1
            case = create_exception_case(
                case_id=f"CASE-{transaction.transaction_id}",
                transaction=transaction,
                result=result,
                evidence_ids=[transaction.transaction_id, result.rate_card_version],
            )
            exceptions.append(case)

            log.append(
                event_id=f"AUD-{transaction.transaction_id}-EXCEPTION",
                event_type="reconciliation.exception.created",
                actor="reconciliation-engine",
                payload={"case_id": case.case_id, "variance_ngn": str(case.variance_ngn)},
                timestamp=_now_iso(),
            )

    log.append(
        event_id=f"AUD-{batch_id}-END",
        event_type="reconciliation.completed",
        actor="system",
        payload={
            "batch_id": batch_id,
            "total_cases": len(pairs),
            "flagged_count": flagged_count,
            "clean_count": len(pairs) - flagged_count,
        },
        timestamp=_now_iso(),
    )

    return ReconciliationBatchResult(
        batch_id=batch_id,
        total_cases=len(pairs),
        flagged_count=flagged_count,
        clean_count=len(pairs) - flagged_count,
        exceptions=exceptions,
        audit_log=log,
    )
