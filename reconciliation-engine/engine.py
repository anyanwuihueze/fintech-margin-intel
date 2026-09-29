"""
Deterministic fee reconciliation engine.

Rule of the whole project: this module is the ONLY place that computes a
naira figure. The AI investigator (added later) explains a variance that
already exists here — it never calculates one. Every function here is pure:
same transaction + same rate card version in, same number out, every time.

Three fee shapes are handled because the three providers genuinely price
differently:
  - Paystack:     percentage + flat fee, with a waiver threshold and a cap
  - Flutterwave:  blended percentage, no flat component
  - NIP:          tiered flat fee + a separate sender-paid stamp duty

VAT (7.5%, Nigeria) applies to the fee amount itself, never to the
transaction principal. NIP carries no VAT (it's a bank levy, not a
processor's commercial fee) and no stamp duty below ₦10,000.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from models import Transaction, ProviderId, Channel, ExpectedFeeResult, VarianceResult
from rate_card_loader import RateCardStore

TWO_DP = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def _expected_fee_paystack(amount: Decimal, channel_config: dict, vat_rate: Decimal) -> dict:
    pct = Decimal(str(channel_config["percentage_fee"]))
    flat = Decimal(str(channel_config["flat_fee_ngn"]))
    waived_under = channel_config.get("flat_fee_waived_under_ngn")
    cap = channel_config.get("fee_cap_ngn")

    if waived_under is not None and amount < Decimal(str(waived_under)):
        base_fee = Decimal("0")
    else:
        base_fee = amount * pct + flat
        if cap is not None:
            base_fee = min(base_fee, Decimal(str(cap)))

    vat = _round(base_fee * vat_rate)
    total = _round(base_fee + vat)

    return {
        "percentage_component": _round(amount * pct),
        "flat_component": flat,
        "cap_applied": cap is not None and (amount * pct + flat) > Decimal(str(cap or "Infinity")),
        "base_fee": _round(base_fee),
        "vat": vat,
        "total": total,
    }


def _expected_fee_flutterwave(amount: Decimal, channel_config: dict, vat_rate: Decimal) -> dict:
    blended = Decimal(str(channel_config["blended_pct"]))
    flat = Decimal(str(channel_config.get("flat_fee_ngn", 0)))
    cap = channel_config.get("fee_cap_ngn")

    base_fee = amount * blended + flat
    if cap is not None:
        base_fee = min(base_fee, Decimal(str(cap)))

    vat = _round(base_fee * vat_rate)
    total = _round(base_fee + vat)

    return {
        "percentage_component": _round(amount * blended),
        "flat_component": flat,
        "cap_applied": False,
        "base_fee": _round(base_fee),
        "vat": vat,
        "total": total,
    }


def _expected_fee_nip(amount: Decimal, channel_config: dict, stamp_duty_config: dict) -> dict:
    tier_fee = Decimal("0")
    for tier in channel_config["tiers"]:
        min_amt = Decimal(str(tier["min_ngn"]))
        max_amt = Decimal(str(tier["max_ngn"])) if tier["max_ngn"] is not None else None
        if amount >= min_amt and (max_amt is None or amount <= max_amt):
            tier_fee = Decimal(str(tier["flat_fee_ngn"]))
            break

    stamp_duty = Decimal("0")
    if amount >= Decimal(str(stamp_duty_config["applies_from_ngn"])):
        stamp_duty = Decimal(str(stamp_duty_config["flat_fee_ngn"]))

    total = _round(tier_fee + stamp_duty)

    return {
        "tier_fee": tier_fee,
        "stamp_duty": stamp_duty,
        "cap_applied": False,
        "base_fee": tier_fee,
        "vat": Decimal("0"),
        "total": total,
    }


def compute_expected_fee(transaction: Transaction, store: RateCardStore) -> ExpectedFeeResult:
    """
    Resolve the correct rate-card version for this transaction's provider
    and timestamp, then compute the expected fee under that provider's
    actual pricing mechanics.
    """
    version = store.resolve(transaction.provider_id, at=transaction.timestamp)
    if version is None:
        raise ValueError(
            f"No rate card found for {transaction.provider_id} at {transaction.timestamp}"
        )

    config = version.raw_config
    channel_key = transaction.channel.value
    amount = Decimal(str(transaction.amount_ngn))

    if transaction.provider_id == ProviderId.PAYSTACK:
        channel_config = config["channels"][channel_key]
        vat_rate = Decimal(str(config["vat_rate"]))
        breakdown = _expected_fee_paystack(amount, channel_config, vat_rate)

    elif transaction.provider_id == ProviderId.FLUTTERWAVE:
        channel_config = config["channels"][channel_key]
        vat_rate = Decimal(str(config["vat_rate"]))
        breakdown = _expected_fee_flutterwave(amount, channel_config, vat_rate)

    elif transaction.provider_id == ProviderId.NIP:
        channel_config = config["channels"][channel_key]
        breakdown = _expected_fee_nip(amount, channel_config, config["stamp_duty"])

    else:
        raise ValueError(f"Unsupported provider: {transaction.provider_id}")

    return ExpectedFeeResult(
        transaction_id=transaction.transaction_id,
        rate_card_version=version.version,
        expected_fee_ngn=breakdown["total"],
        breakdown=breakdown,
    )


def compute_variance(
    transaction: Transaction,
    actual_fee_ngn: Decimal,
    store: RateCardStore,
    flag_threshold_ngn: Decimal = Decimal("1.00"),
) -> VarianceResult:
    """
    Compare expected vs. actual fee for a transaction. Flags anything above
    flag_threshold_ngn — deliberately low, since even small variances compound
    at volume (see: the fee-drift literature on basis-point leakage at scale).
    """
    expected = compute_expected_fee(transaction, store)
    actual = Decimal(str(actual_fee_ngn))
    variance = _round(actual - expected.expected_fee_ngn)

    variance_pct = None
    if expected.expected_fee_ngn != 0:
        variance_pct = _round((variance / expected.expected_fee_ngn) * 100)

    return VarianceResult(
        transaction_id=transaction.transaction_id,
        rate_card_version=expected.rate_card_version,
        expected_fee_ngn=expected.expected_fee_ngn,
        actual_fee_ngn=actual,
        variance_ngn=variance,
        variance_pct=variance_pct,
        flagged=abs(variance) >= flag_threshold_ngn,
    )
