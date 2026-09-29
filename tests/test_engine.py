"""
Every expected value in this file is hand-calculated from the documented
rate cards, not copied from the engine's own output. Two NIP cases
(test_nip_transfer_10k_to_50k_matches_cbn_example and
test_nip_transfer_above_50k_matches_cbn_example) reproduce figures published
directly in CBN's 2026 Guide to Charges coverage — the strongest possible
proof the tier+stamp-duty logic is correct, since they weren't derived from
our own code at all.
"""
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "reconciliation-engine"))

from models import Transaction, ProviderId, Channel
from rate_card_loader import RateCardStore
from engine import compute_expected_fee, compute_variance

STORE = RateCardStore()
NOW = datetime(2026, 6, 1)


def make_tx(provider, channel, amount, tx_id="TX-TEST"):
    return Transaction(
        transaction_id=tx_id,
        provider_id=provider,
        channel=channel,
        amount_ngn=Decimal(str(amount)),
        timestamp=NOW,
        customer_account_ref="ACC-0001",
    )


# --- Paystack ---

def test_paystack_local_card_10k():
    # 1.5% * 10,000 + 100 = 150 + 100 = 250 base fee. VAT 7.5% of 250 = 18.75.
    # Matches Paystack's own published example of ₦250 base fee for ₦10,000.
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "10000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("250.00")
    assert result.breakdown["vat"] == Decimal("18.75")
    assert result.expected_fee_ngn == Decimal("268.75")


def test_paystack_local_card_cap_applies_at_200k():
    # Uncapped fee would be 1.5%*200,000+100 = 3,100. Capped at 2,000.
    # Matches Paystack's own published capped example.
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "200000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("2000.00")
    assert result.breakdown["cap_applied"] is True


def test_paystack_local_card_waived_under_2500():
    # Below ₦2,500 → flat fee waived entirely per Paystack docs.
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "2000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("0")
    assert result.expected_fee_ngn == Decimal("0.00")


def test_paystack_international_card_no_cap():
    # 3.9% * 50,000 + 100 = 1950 + 100 = 2050. No cap on international.
    tx = make_tx(ProviderId.PAYSTACK, Channel.INTERNATIONAL_CARD, "50000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("2050.00")


# --- Flutterwave ---

def test_flutterwave_local_card_10k():
    # Blended 2% * 10,000 = 200 base fee. VAT 7.5% of 200 = 15.
    tx = make_tx(ProviderId.FLUTTERWAVE, Channel.LOCAL_CARD, "10000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("200.00")
    assert result.breakdown["vat"] == Decimal("15.00")
    assert result.expected_fee_ngn == Decimal("215.00")


def test_flutterwave_international_card_higher_rate():
    # Blended 4.8% * 50,000 = 2,400.
    tx = make_tx(ProviderId.FLUTTERWAVE, Channel.INTERNATIONAL_CARD, "50000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["base_fee"] == Decimal("2400.00")


# --- NIP (CBN 2026 Guide to Charges) ---

def test_nip_transfer_under_5k_is_free():
    tx = make_tx(ProviderId.NIP, Channel.BANK_TRANSFER, "3000")
    result = compute_expected_fee(tx, STORE)
    assert result.expected_fee_ngn == Decimal("0.00")


def test_nip_transfer_10k_to_50k_matches_cbn_example():
    # CBN's own published example: a ₦10,000+ transfer in the 5k-50k tier
    # costs ₦10 bank fee + ₦50 stamp duty = ₦60 total, sender-paid.
    tx = make_tx(ProviderId.NIP, Channel.BANK_TRANSFER, "30000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["tier_fee"] == Decimal("10")
    assert result.breakdown["stamp_duty"] == Decimal("50")
    assert result.expected_fee_ngn == Decimal("60.00")


def test_nip_transfer_above_50k_matches_cbn_example():
    # CBN's own published example: transfers above ₦50,000 cost ₦50 bank fee
    # + ₦50 stamp duty = ₦100 total.
    tx = make_tx(ProviderId.NIP, Channel.BANK_TRANSFER, "100000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["tier_fee"] == Decimal("50")
    assert result.breakdown["stamp_duty"] == Decimal("50")
    assert result.expected_fee_ngn == Decimal("100.00")


def test_nip_no_stamp_duty_below_10k():
    # ₦5,000-₦9,999.99 pays the ₦10 tier fee but no stamp duty (threshold is ₦10,000).
    tx = make_tx(ProviderId.NIP, Channel.BANK_TRANSFER, "8000")
    result = compute_expected_fee(tx, STORE)
    assert result.breakdown["tier_fee"] == Decimal("10")
    assert result.breakdown["stamp_duty"] == Decimal("0")
    assert result.expected_fee_ngn == Decimal("10.00")


# --- Variance detection ---

def test_variance_flags_misclassified_tier():
    # A ₦10,000 Paystack local-card transaction (expected ₦268.75) that got
    # charged the international rate instead — the classic misclassification
    # exception the whole system exists to catch.
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "10000")
    result = compute_variance(tx, actual_fee_ngn=Decimal("490.00"), store=STORE)
    assert result.flagged is True
    assert result.variance_ngn == Decimal("221.25")


def test_variance_not_flagged_when_exact_match():
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "10000")
    result = compute_variance(tx, actual_fee_ngn=Decimal("268.75"), store=STORE)
    assert result.flagged is False
    assert result.variance_ngn == Decimal("0.00")


def test_variance_negative_when_undercharged():
    tx = make_tx(ProviderId.PAYSTACK, Channel.LOCAL_CARD, "10000")
    result = compute_variance(tx, actual_fee_ngn=Decimal("200.00"), store=STORE)
    assert result.flagged is True
    assert result.variance_ngn == Decimal("-68.75")
