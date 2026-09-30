"""
Exception/case model for reconciliation anomalies.

The deterministic reconciliation engine remains the source of financial truth.
This layer records the resulting exception as an auditable case.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from models import Transaction, VarianceResult


class ExceptionStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ExceptionCase(BaseModel):
    case_id: str
    transaction_id: str
    provider_id: str
    rate_card_version: str

    expected_fee_ngn: Decimal
    actual_fee_ngn: Decimal
    variance_ngn: Decimal
    variance_pct: Decimal | None = None

    status: ExceptionStatus = ExceptionStatus.OPEN
    evidence_ids: list[str] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def create_exception_case(
    *,
    case_id: str,
    transaction: Transaction,
    result: VarianceResult,
    evidence_ids: list[str] | None = None,
) -> ExceptionCase:
    """
    Create an auditable case only when reconciliation has flagged a variance.

    Provider identity comes from the original transaction, not from the
    reconciliation result or caller-supplied free text.
    """
    if not result.flagged:
        raise ValueError(
            "Cannot create an exception case for an unflagged reconciliation result."
        )

    if result.transaction_id != transaction.transaction_id:
        raise ValueError(
            "Transaction ID mismatch between transaction and reconciliation result."
        )

    return ExceptionCase(
        case_id=case_id,
        transaction_id=transaction.transaction_id,
        provider_id=transaction.provider_id.value,
        rate_card_version=result.rate_card_version,
        expected_fee_ngn=result.expected_fee_ngn,
        actual_fee_ngn=result.actual_fee_ngn,
        variance_ngn=result.variance_ngn,
        variance_pct=result.variance_pct,
        evidence_ids=evidence_ids or [],
    )
