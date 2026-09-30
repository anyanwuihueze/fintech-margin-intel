import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "reconciliation-engine"))

from audit import AuditLog


def test_audit_chain_starts_with_genesis_hash():
    log = AuditLog()

    event = log.append(
        event_id="AUD-001",
        event_type="reconciliation.exception.created",
        actor="reconciliation-engine",
        payload={"case_id": "CASE-S02", "variance_ngn": "221.25"},
        timestamp="2026-06-01T12:00:00+00:00",
    )

    assert event.previous_hash == AuditLog.GENESIS_HASH
    assert len(event.event_hash) == 64
    assert log.verify()


def test_audit_chain_links_events():
    log = AuditLog()

    first = log.append(
        event_id="AUD-001",
        event_type="reconciliation.started",
        actor="system",
        payload={"batch_id": "BATCH-SYN-001"},
        timestamp="2026-06-01T12:00:00+00:00",
    )

    second = log.append(
        event_id="AUD-002",
        event_type="reconciliation.exception.created",
        actor="reconciliation-engine",
        payload={"case_id": "CASE-S02", "variance_ngn": "221.25"},
        timestamp="2026-06-01T12:00:01+00:00",
    )

    assert second.previous_hash == first.event_hash
    assert first.event_hash != second.event_hash
    assert log.verify()


def test_audit_detects_payload_tampering():
    log = AuditLog()

    event = log.append(
        event_id="AUD-001",
        event_type="reconciliation.exception.created",
        actor="reconciliation-engine",
        payload={"case_id": "CASE-S02", "variance_ngn": "221.25"},
        timestamp="2026-06-01T12:00:00+00:00",
    )

    event.payload["variance_ngn"] = "0.00"

    assert not log.verify()


def test_audit_detects_event_reordering():
    log = AuditLog()

    log.append(
        event_id="AUD-001",
        event_type="reconciliation.started",
        actor="system",
        payload={"batch_id": "BATCH-SYN-001"},
        timestamp="2026-06-01T12:00:00+00:00",
    )

    log.append(
        event_id="AUD-002",
        event_type="reconciliation.exception.created",
        actor="reconciliation-engine",
        payload={"case_id": "CASE-S02"},
        timestamp="2026-06-01T12:00:01+00:00",
    )

    log._events.reverse()

    assert not log.verify()


def test_audit_export_is_serializable():
    log = AuditLog()

    log.append(
        event_id="AUD-001",
        event_type="reconciliation.started",
        actor="system",
        payload={"batch_id": "BATCH-SYN-001"},
        timestamp="2026-06-01T12:00:00+00:00",
    )

    exported = log.export()

    assert len(exported) == 1
    assert exported[0]["event_id"] == "AUD-001"
    assert exported[0]["event_hash"]
    assert exported[0]["previous_hash"] == AuditLog.GENESIS_HASH
