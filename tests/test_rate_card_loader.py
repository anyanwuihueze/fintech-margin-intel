import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "reconciliation-engine"))

from models import ProviderId
from rate_card_loader import RateCardStore


def test_resolves_paystack_current_version():
    store = RateCardStore()
    result = store.resolve(ProviderId.PAYSTACK, at=datetime(2026, 6, 1))
    assert result is not None
    assert result.version == "2026.1"
    assert result.provider_id == ProviderId.PAYSTACK


def test_resolves_flutterwave_current_version():
    store = RateCardStore()
    result = store.resolve(ProviderId.FLUTTERWAVE, at=datetime(2026, 6, 1))
    assert result is not None
    assert result.version == "2026.1"


def test_resolves_nip_current_version():
    store = RateCardStore()
    result = store.resolve(ProviderId.NIP, at=datetime(2026, 6, 1))
    assert result is not None
    assert result.version == "2026.1"


def test_returns_none_before_any_version_existed():
    store = RateCardStore()
    result = store.resolve(ProviderId.PAYSTACK, at=datetime(2020, 1, 1))
    assert result is None


def test_all_versions_returns_only_matching_provider():
    store = RateCardStore()
    versions = store.all_versions(ProviderId.NIP)
    assert all(v.provider_id == ProviderId.NIP for v in versions)
    assert len(versions) >= 1
