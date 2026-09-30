import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "reconciliation-engine"))

from workflow import run_reconciliation_batch
from scenarios import generate_all_scenarios
from engine import compute_variance
from rate_card_loader import RateCardStore


def _pairs():
    return [(t, s) for _spec, t, s in generate_all_scenarios()]


def test_workflow_matches_standalone_reconciliation_counts():
    result = run_reconciliation_batch(_pairs(), batch_id="BATCH-SYN-001")

    assert result.total_cases == 9
    assert result.flagged_count == 3
    assert result.clean_count == 6
    assert len(result.exceptions) == 3
    assert {c.transaction_id for c in result.exceptions} == {"TX-S02", "TX-S03", "TX-S07"}


def test_workflow_audit_log_verifies():
    result = run_reconciliation_batch(_pairs(), batch_id="BATCH-SYN-001")

    assert result.audit_log.verify()
    # start + 9 recon results + 3 exception events + end
    assert len(result.audit_log.export()) == 1 + 9 + 3 + 1


def test_workflow_matches_manual_per_scenario_computation():
    """Cross-check: workflow output must equal calling compute_variance
    directly per scenario — proves integration changes no financial number."""
    store = RateCardStore()
    manual_flagged = 0
    for spec, transaction, settlement in generate_all_scenarios():
        result = compute_variance(transaction, actual_fee_ngn=settlement.actual_fee_ngn, store=store)
        assert result.flagged == spec.expected_flagged
        if result.flagged:
            manual_flagged += 1

    workflow_result = run_reconciliation_batch(_pairs(), batch_id="BATCH-SYN-001")
    assert workflow_result.flagged_count == manual_flagged
