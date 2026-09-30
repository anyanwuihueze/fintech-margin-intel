"""
Tamper-evident append-only audit log.

Design:
- Events are append-only.
- Each event contains the SHA-256 hash of the previous event.
- The event hash covers the complete canonical event payload.
- Any modification, deletion, insertion, or reordering breaks the chain.
- No secrets or credentials belong in audit events.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _canonical_json(payload: dict[str, Any]) -> str:
    """Return deterministic JSON suitable for hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditEvent:
    """Single immutable audit event represented as a dictionary."""

    def __init__(
        self,
        *,
        event_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        previous_hash: str,
        timestamp: str | None = None,
    ) -> None:
        self.event_id = event_id
        self.event_type = event_type
        self.actor = actor
        self.payload = payload
        self.previous_hash = previous_hash
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        unsigned = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
        }

        self.event_hash = _sha256(_canonical_json(unsigned))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "event_hash": self.event_hash,
        }


class AuditLog:
    """In-memory append-only hash chain for the Day 5 control layer."""

    GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        """Expose an immutable view of the event sequence."""
        return tuple(self._events)

    def append(
        self,
        *,
        event_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        timestamp: str | None = None,
    ) -> AuditEvent:
        """Append exactly one new event to the chain."""
        previous_hash = (
            self._events[-1].event_hash
            if self._events
            else self.GENESIS_HASH
        )

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            previous_hash=previous_hash,
            timestamp=timestamp,
        )

        self._events.append(event)
        return event

    def verify(self) -> bool:
        """
        Verify the entire chain.

        Returns False if any event was modified, removed, inserted,
        reordered, or otherwise disconnected from the chain.
        """
        previous_hash = self.GENESIS_HASH

        for event in self._events:
            unsigned = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "payload": event.payload,
                "previous_hash": event.previous_hash,
                "timestamp": event.timestamp,
            }

            expected_hash = _sha256(_canonical_json(unsigned))

            if event.previous_hash != previous_hash:
                return False

            if event.event_hash != expected_hash:
                return False

            previous_hash = event.event_hash

        return True

    def export(self) -> list[dict[str, Any]]:
        """Return a serializable representation of the complete chain."""
        return [event.to_dict() for event in self._events]
