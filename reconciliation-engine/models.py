"""
Core data models for the reconciliation engine.

Design rule: rate cards are immutable once published. A transaction is always
reconciled against the rate-card version that was active at its timestamp,
never against "whatever the current rate card says." This is what makes the
audit trail defensible — you can always answer "what rule applied, and when."
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Channel(str, Enum):
    LOCAL_CARD = "local_card"
    INTERNATIONAL_CARD = "international_card"
    BANK_TRANSFER = "bank_transfer"
    USSD = "ussd"
    MOBILE_MONEY = "mobile_money"


class ProviderId(str, Enum):
    PAYSTACK = "paystack"
    FLUTTERWAVE = "flutterwave"
    NIP = "nip"


class Transaction(BaseModel):
    transaction_id: str
    provider_id: ProviderId
    channel: Channel
    amount_ngn: Decimal
    timestamp: datetime
    customer_account_ref: str = Field(..., description="Pseudonymous reference, never a real account number in synthetic data")
    status: str = "completed"


class SettlementRecord(BaseModel):
    """What the provider actually charged us, per their settlement/statement file."""
    settlement_id: str
    transaction_id: str
    provider_id: ProviderId
    actual_fee_ngn: Decimal
    settlement_batch_id: str
    settled_at: datetime


class RateCardVersion(BaseModel):
    provider_id: ProviderId
    version: str
    effective_date: datetime
    source: str
    raw_config: dict = Field(..., description="Raw JSON block from providers.json for this provider+version")


class ExpectedFeeResult(BaseModel):
    transaction_id: str
    rate_card_version: str
    expected_fee_ngn: Decimal
    breakdown: dict = Field(..., description="Line-item breakdown: percentage component, flat component, cap applied, VAT, levies")


class VarianceResult(BaseModel):
    transaction_id: str
    rate_card_version: str
    expected_fee_ngn: Decimal
    actual_fee_ngn: Decimal
    variance_ngn: Decimal
    variance_pct: Optional[Decimal] = None
    flagged: bool = False
