import pytest

from sylvie_runtime.billing import (
    ExchangeWallet, InsufficientCreditsError, DuplicateRequestError
)


def test_five_free_then_quarter_per_exchange(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    for index in range(5):
        reservation = wallet.begin_exchange("alice", f"free-{index}")
        assert reservation.payment_kind == "free"
        wallet.complete_exchange("alice", reservation.reservation_id)
    assert wallet.get_wallet("alice").free_exchanges_remaining == 0
    wallet.credit_wallet("alice", 100, verified_payment_event_id="evt_topup_1")
    reservation = wallet.begin_exchange("alice", "paid-1")
    assert reservation.payment_kind == "credit"
    assert wallet.get_wallet("alice").credit_balance_cents == 75
    wallet.complete_exchange("alice", reservation.reservation_id)


def test_provider_failure_releases_paid_reservation(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    wallet.credit_wallet("alice", 50, verified_payment_event_id="evt_topup_2")
    reservation = wallet.begin_exchange("alice", "request-1")
    wallet.fail_exchange("alice", reservation.reservation_id)
    assert wallet.get_wallet("alice").credit_balance_cents == 50


def test_insufficient_balance_blocks_paid_exchange(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    for index in range(5):
        reservation = wallet.begin_exchange("alice", f"free-{index}")
        wallet.complete_exchange("alice", reservation.reservation_id)
    with pytest.raises(InsufficientCreditsError):
        wallet.begin_exchange("alice", "paid-without-credit")


def test_duplicate_payment_event_is_idempotent(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    assert wallet.credit_wallet("alice", 500, verified_payment_event_id="evt_same") is True
    assert wallet.credit_wallet("alice", 500, verified_payment_event_id="evt_same") is False
    assert wallet.get_wallet("alice").credit_balance_cents == 500


def test_duplicate_exchange_request_cannot_double_charge(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    wallet.credit_wallet("alice", 100, verified_payment_event_id="evt_topup_3")
    reservation = wallet.begin_exchange("alice", "same-request")
    wallet.complete_exchange("alice", reservation.reservation_id)
    with pytest.raises(DuplicateRequestError):
        wallet.begin_exchange("alice", "same-request")
    assert wallet.get_wallet("alice").credit_balance_cents == 75


def test_concurrent_free_reservations_do_not_overbook(tmp_path):
    wallet = ExchangeWallet(tmp_path / "wallet.db")
    reservations = [wallet.begin_exchange("alice", f"free-{i}") for i in range(5)]
    assert all(r.payment_kind == "free" for r in reservations)
    with pytest.raises(InsufficientCreditsError):
        wallet.begin_exchange("alice", "sixth")
