"""
Deterministic synthetic scenarios for reconciliation testing.

Day 4 rule:
- ScenarioSpec contains the ground truth.
- The scenario generator creates synthetic transaction + settlement data.
- The existing deterministic reconciliation engine remains the source of
  computed truth.
- Tests compare the engine result against independently specified ground truth.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel

from models import (
    Channel,
    ProviderId,
    SettlementRecord,
    Transaction,
)


class ScenarioSpec(BaseModel):
    scenario_id: str
    description: str
    provider_id: ProviderId
    channel: Channel
    amount_ngn: Decimal
    actual_fee_ngn: Decimal
    expected_fee_ngn: Decimal
    expected_variance_ngn: Decimal
    expected_flagged: bool


SCENARIOS: List[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="S01",
        description="Paystack local card exact match",
        provider_id=ProviderId.PAYSTACK,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("10000"),
        actual_fee_ngn=Decimal("268.75"),
        expected_fee_ngn=Decimal("268.75"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
    ScenarioSpec(
        scenario_id="S02",
        description="Paystack local card misclassified as international",
        provider_id=ProviderId.PAYSTACK,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("10000"),
        actual_fee_ngn=Decimal("490.00"),
        expected_fee_ngn=Decimal("268.75"),
        expected_variance_ngn=Decimal("221.25"),
        expected_flagged=True,
    ),
    ScenarioSpec(
        scenario_id="S03",
        description="Paystack local card undercharge",
        provider_id=ProviderId.PAYSTACK,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("10000"),
        actual_fee_ngn=Decimal("200.00"),
        expected_fee_ngn=Decimal("268.75"),
        expected_variance_ngn=Decimal("-68.75"),
        expected_flagged=True,
    ),
    ScenarioSpec(
        scenario_id="S04",
        description="Paystack local card flat fee waiver",
        provider_id=ProviderId.PAYSTACK,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("2000"),
        actual_fee_ngn=Decimal("0.00"),
        expected_fee_ngn=Decimal("0.00"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
    ScenarioSpec(
        scenario_id="S05",
        description="Paystack local card fee cap exact match",
        provider_id=ProviderId.PAYSTACK,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("200000"),
        actual_fee_ngn=Decimal("2150.00"),
        expected_fee_ngn=Decimal("2150.00"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
    ScenarioSpec(
        scenario_id="S06",
        description="Flutterwave local card exact match",
        provider_id=ProviderId.FLUTTERWAVE,
        channel=Channel.LOCAL_CARD,
        amount_ngn=Decimal("10000"),
        actual_fee_ngn=Decimal("215.00"),
        expected_fee_ngn=Decimal("215.00"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
    ScenarioSpec(
        scenario_id="S07",
        description="Flutterwave international card overcharge",
        provider_id=ProviderId.FLUTTERWAVE,
        channel=Channel.INTERNATIONAL_CARD,
        amount_ngn=Decimal("50000"),
        actual_fee_ngn=Decimal("2630.00"),
        expected_fee_ngn=Decimal("2580.00"),
        expected_variance_ngn=Decimal("50.00"),
        expected_flagged=True,
    ),
    ScenarioSpec(
        scenario_id="S08",
        description="NIP 30k transfer exact CBN-style fee",
        provider_id=ProviderId.NIP,
        channel=Channel.BANK_TRANSFER,
        amount_ngn=Decimal("30000"),
        actual_fee_ngn=Decimal("60.00"),
        expected_fee_ngn=Decimal("60.00"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
    ScenarioSpec(
        scenario_id="S09",
        description="NIP 3k transfer free tier exact match",
        provider_id=ProviderId.NIP,
        channel=Channel.BANK_TRANSFER,
        amount_ngn=Decimal("3000"),
        actual_fee_ngn=Decimal("0.00"),
        expected_fee_ngn=Decimal("0.00"),
        expected_variance_ngn=Decimal("0.00"),
        expected_flagged=False,
    ),
]


def generate_scenario(spec: ScenarioSpec) -> tuple[Transaction, SettlementRecord]:
    """
    Turn an immutable scenario specification into synthetic transaction
    and settlement records.

    Fixed timestamps and IDs make the generator deterministic and reproducible.
    """
    timestamp = datetime(2026, 6, 1, 12, 0, 0)

    transaction = Transaction(
        transaction_id=f"TX-{spec.scenario_id}",
        provider_id=spec.provider_id,
        channel=spec.channel,
        amount_ngn=spec.amount_ngn,
        timestamp=timestamp,
        customer_account_ref=f"ACC-SYN-{spec.scenario_id}",
        status="completed",
    )

    settlement = SettlementRecord(
        settlement_id=f"SET-{spec.scenario_id}",
        transaction_id=transaction.transaction_id,
        provider_id=spec.provider_id,
        actual_fee_ngn=spec.actual_fee_ngn,
        settlement_batch_id="BATCH-SYN-001",
        settled_at=timestamp,
    )

    return transaction, settlement


def generate_all_scenarios() -> list[tuple[ScenarioSpec, Transaction, SettlementRecord]]:
    return [
        (spec, *generate_scenario(spec))
        for spec in SCENARIOS
    ]
