from decimal import Decimal

from economics import EconomicsScenario, simulate_economics


def test_one_million_transactions_one_percent_five_naira():
    scenario = EconomicsScenario(
        transactions_per_month=1_000_000,
        discrepancy_rate=Decimal("0.01"),
        average_variance_ngn=Decimal("5.00"),
    )

    result = simulate_economics(scenario)

    assert result.modeled_exception_count == 10_000
    assert result.modeled_monthly_exposure_ngn == Decimal("50000.00")
    assert result.modeled_annual_exposure_ngn == Decimal("600000.00")


def test_recovery_rate_models_recoverable_exposure():
    scenario = EconomicsScenario(
        transactions_per_month=1_000_000,
        discrepancy_rate=Decimal("0.01"),
        average_variance_ngn=Decimal("5.00"),
        recovery_rate=Decimal("0.50"),
    )

    result = simulate_economics(scenario)

    assert result.modeled_monthly_exposure_ngn == Decimal("50000.00")
    assert result.modeled_annual_exposure_ngn == Decimal("600000.00")
    assert result.modeled_monthly_recoverable_ngn == Decimal("25000.00")
    assert result.modeled_annual_recoverable_ngn == Decimal("300000.00")


def test_fractional_exception_count_is_deterministically_rounded():
    scenario = EconomicsScenario(
        transactions_per_month=101,
        discrepancy_rate=Decimal("0.005"),
        average_variance_ngn=Decimal("10.00"),
    )

    result = simulate_economics(scenario)

    assert result.modeled_exception_count == 1
    assert result.modeled_monthly_exposure_ngn == Decimal("10.00")


def test_zero_recovery_is_default():
    scenario = EconomicsScenario(
        transactions_per_month=100_000,
        discrepancy_rate=Decimal("0.005"),
        average_variance_ngn=Decimal("25.00"),
    )

    result = simulate_economics(scenario)

    assert result.recovery_rate == Decimal("0")
    assert result.modeled_monthly_recoverable_ngn == Decimal("0.00")
    assert result.modeled_annual_recoverable_ngn == Decimal("0.00")


def test_decimal_money_rounding():
    scenario = EconomicsScenario(
        transactions_per_month=100,
        discrepancy_rate=Decimal("0.01"),
        average_variance_ngn=Decimal("1.237"),
    )

    result = simulate_economics(scenario)

    assert result.average_variance_ngn == Decimal("1.24")
    assert result.modeled_monthly_exposure_ngn == Decimal("1.24")


def test_invalid_discrepancy_rate_rejected():
    try:
        EconomicsScenario(
            transactions_per_month=100,
            discrepancy_rate=Decimal("1.01"),
            average_variance_ngn=Decimal("5.00"),
        )
        assert False, "Expected validation error"
    except ValueError:
        pass


def test_invalid_recovery_rate_rejected():
    try:
        EconomicsScenario(
            transactions_per_month=100,
            discrepancy_rate=Decimal("0.01"),
            average_variance_ngn=Decimal("5.00"),
            recovery_rate=Decimal("1.01"),
        )
        assert False, "Expected validation error"
    except ValueError:
        pass
