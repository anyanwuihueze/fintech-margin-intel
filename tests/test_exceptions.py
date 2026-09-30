import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "reconciliation-engine"))

from exceptions import ExceptionStatus, create_exception_case
from scenarios import generate_all_scenarios
from engine import compute_variance
from rate_card_loader import RateCardStore


def test_exception_case_preserves_provider_identity():
    spec, transaction, _settlement = generate_all_scenarios()[1]

    result = compute_variance(
        transaction,
        actual_fee_ngn=Decimal("490.00"),
        store=RateCardStore(),
    )

    case = create_exception_case(
        case_id="CASE-S02",
        transaction=transaction,
        result=result,
        evidence_ids=["TX-S02", "RATE-2026.1"],
    )

    assert case.case_id == "CASE-S02"
    assert case.transaction_id == "TX-S02"
    assert case.provider_id == spec.provider_id.value
    assert case.expected_fee_ngn == Decimal("268.75")
    assert case.actual_fee_ngn == Decimal("490.00")
    assert case.variance_ngn == Decimal("221.25")
    assert case.status == ExceptionStatus.OPEN
    assert case.evidence_ids == ["TX-S02", "RATE-2026.1"]


def test_exception_case_rejects_clean_reconciliation():
    _spec, transaction, settlement = generate_all_scenarios()[0]

    result = compute_variance(
        transaction,
        actual_fee_ngn=settlement.actual_fee_ngn,
        store=RateCardStore(),
    )

    assert result.flagged is False

    with pytest.raises(ValueError, match="unflagged"):
        create_exception_case(
            case_id="CASE-S01",
            transaction=transaction,
            result=result,
        )


def test_exception_case_rejects_transaction_mismatch():
    _spec, transaction, settlement = generate_all_scenarios()[1]

    result = compute_variance(
        transaction,
        actual_fee_ngn=settlement.actual_fee_ngn,
        store=RateCardStore(),
    )

    from models import Transaction

    mismatched = Transaction(
        transaction_id="TX-WRONG",
        provider_id=transaction.provider_id,
        channel=transaction.channel,
        amount_ngn=transaction.amount_ngn,
        timestamp=transaction.timestamp,
        customer_account_ref=transaction.customer_account_ref,
        status=transaction.status,
    )

    with pytest.raises(ValueError, match="Transaction ID mismatch"):
        create_exception_case(
            case_id="CASE-S02",
            transaction=mismatched,
            result=result,
        )
