"""
Loads rate cards from rate-cards/providers.json and resolves which version
was active at a given transaction timestamp.

Rule: rate cards are never mutated in place. A new pricing change ships as a
new version entry with its own effective_date. Reconciliation always looks up
"the version active when the transaction happened," not "the current version."
This means a rate change next month doesn't silently rewrite last month's
expected-fee calculations.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import ProviderId, RateCardVersion

RATE_CARDS_PATH = Path(__file__).parent.parent / "rate-cards" / "providers.json"


class RateCardStore:
    def __init__(self, path: Path = RATE_CARDS_PATH):
        self._path = path
        self._versions: list[RateCardVersion] = []
        self._load()

    def _load(self) -> None:
        with open(self._path) as f:
            data = json.load(f)

        for provider_block in data["providers"]:
            self._versions.append(
                RateCardVersion(
                    provider_id=ProviderId(provider_block["provider_id"]),
                    version=provider_block["version"],
                    effective_date=datetime.fromisoformat(provider_block["effective_date"]),
                    source=provider_block["source"],
                    raw_config=provider_block,
                )
            )

    def resolve(self, provider_id: ProviderId, at: datetime) -> Optional[RateCardVersion]:
        """
        Return the rate-card version active for provider_id at timestamp `at`:
        the most recent version whose effective_date <= at.

        Today there's exactly one version per provider (2026.1). This method
        exists so that when a provider changes pricing (e.g. Flutterwave's
        Nov 2024 international-fee increase), adding a new versioned entry
        to providers.json is enough — no reconciliation-engine code changes,
        and historical transactions still resolve to the version that was
        actually in force when they happened.
        """
        candidates = [
            v for v in self._versions
            if v.provider_id == provider_id and v.effective_date <= at
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda v: v.effective_date)

    def all_versions(self, provider_id: ProviderId) -> list[RateCardVersion]:
        return [v for v in self._versions if v.provider_id == provider_id]
