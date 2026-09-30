"""
Deterministic economics/exposure simulator.

This module does NOT calculate financial truth from transactions.
It models the potential economic exposure implied by user-supplied
operating assumptions.

All monetary calculations use Decimal.
Results must be labeled as modeled scenarios, not actual customer losses.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, validator


MONEY = Decimal("0.01")
COUNT = Decimal("1")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class EconomicsScenario(BaseModel):
    """
    User-supplied assumptions for a modeled payment-operation scenario.

    discrepancy_rate and recovery_rate are decimal fractions:
      0.01 = 1%
      0.50 = 50%
    """

    transactions_per_month: int = Field(..., gt=0)
    discrepancy_rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("1"))
    average_variance_ngn: Decimal = Field(..., ge=Decimal("0"))
    recovery_rate: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    @validator("average_variance_ngn")
    def validate_variance(cls, value: Decimal) -> Decimal:
        return _money(value)


class EconomicsResult(BaseModel):
    """Deterministic outputs from an EconomicsScenario."""

    transactions_per_month: int
    discrepancy_rate: Decimal
    average_variance_ngn: Decimal
    recovery_rate: Decimal

    modeled_exception_count: int
    modeled_monthly_exposure_ngn: Decimal
    modeled_annual_exposure_ngn: Decimal
    modeled_monthly_recoverable_ngn: Decimal
    modeled_annual_recoverable_ngn: Decimal


def simulate_economics(scenario: EconomicsScenario) -> EconomicsResult:
    """
    Calculate modeled exception volume and economic exposure.

    Exception count is rounded to the nearest whole transaction using
    ROUND_HALF_UP. Monetary values are rounded to two decimal places.

    Formula:
        exceptions = monthly transactions × discrepancy rate
        exposure = exceptions × average variance
        recoverable = exposure × recovery rate
    """

    exception_count = (
        Decimal(scenario.transactions_per_month)
        * scenario.discrepancy_rate
    ).quantize(COUNT, rounding=ROUND_HALF_UP)

    modeled_monthly_exposure = _money(
        exception_count * scenario.average_variance_ngn
    )

    modeled_annual_exposure = _money(
        modeled_monthly_exposure * Decimal("12")
    )

    modeled_monthly_recoverable = _money(
        modeled_monthly_exposure * scenario.recovery_rate
    )

    modeled_annual_recoverable = _money(
        modeled_annual_exposure * scenario.recovery_rate
    )

    return EconomicsResult(
        transactions_per_month=scenario.transactions_per_month,
        discrepancy_rate=scenario.discrepancy_rate,
        average_variance_ngn=scenario.average_variance_ngn,
        recovery_rate=scenario.recovery_rate,
        modeled_exception_count=int(exception_count),
        modeled_monthly_exposure_ngn=modeled_monthly_exposure,
        modeled_annual_exposure_ngn=modeled_annual_exposure,
        modeled_monthly_recoverable_ngn=modeled_monthly_recoverable,
        modeled_annual_recoverable_ngn=modeled_annual_recoverable,
    )
