from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone


FREE_EXCHANGES = 5
EXCHANGE_PRICE_CENTS = 25


@dataclass(frozen=True)
class ExchangeReservation:
    reservation_id: str
    user_id: str
    request_id: str
    payment_kind: str


@dataclass(frozen=True)
class Wallet:
    user_id: str
    free_exchanges_remaining: int
    credit_balance_cents: int


class ExchangeBillingError(Exception):
    """Base class for exchange billing errors."""


class InsufficientCreditsError(ExchangeBillingError):
    pass


class DuplicateRequestError(ExchangeBillingError):
    pass


class ExchangeWallet:
    """SQLite ledger for 5 free successful exchanges, then $0.25 per exchange.

    This is a billing-policy/ledger foundation, not a complete Stripe integration.
    Credit top-ups must only be applied by a trusted server handler after verifying
    the Stripe webhook signature, payment status, amount, currency, and metadata.
    Never expose credit_wallet() directly to a browser or accept client-supplied
    payment verification.
    """

    def __init__(self, database_path: str | Path, *, free_exchanges: int = FREE_EXCHANGES,
                 exchange_price_cents: int = EXCHANGE_PRICE_CENTS) -> None:
        if free_exchanges < 0 or exchange_price_cents < 1:
            raise ValueError("Billing limits must be non-negative and price must be positive.")
        self.database_path = str(database_path)
        self.free_exchanges = free_exchanges
        self.exchange_price_cents = exchange_price_cents
        self._lock = RLock()
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS exchange_wallets (
                    user_id TEXT PRIMARY KEY,
                    free_remaining INTEGER NOT NULL,
                    balance_cents INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS exchange_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    payment_kind TEXT NOT NULL CHECK(payment_kind IN ('free','credit')),
                    amount_cents INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','completed','failed')),
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, request_id)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS exchange_topups (
                    payment_event_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_exchange_reservations_user_status ON exchange_reservations(user_id,status)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _user(user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 200:
            raise ValueError("A valid authenticated user_id is required.")
        return user_id.strip()

    def _ensure_wallet(self, db: sqlite3.Connection, user_id: str) -> None:
        db.execute(
            "INSERT OR IGNORE INTO exchange_wallets(user_id,free_remaining,balance_cents,created_at) VALUES(?,?,0,?)",
            (user_id, self.free_exchanges, datetime.now(timezone.utc).isoformat()),
        )

    def begin_exchange(self, user_id: str, request_id: str) -> ExchangeReservation:
        """Reserve one free exchange or 25 cents before invoking the AI provider."""
        user_id = self._user(user_id)
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 200:
            raise ValueError("A stable request_id is required for idempotency.")
        request_id = request_id.strip()
        with self._lock:
            db = self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                self._ensure_wallet(db, user_id)
                existing = db.execute(
                    "SELECT * FROM exchange_reservations WHERE user_id=? AND request_id=?",
                    (user_id, request_id),
                ).fetchone()
                if existing:
                    if existing["status"] == "pending":
                        db.execute("COMMIT")
                        return ExchangeReservation(existing["reservation_id"], user_id, request_id, existing["payment_kind"])
                    raise DuplicateRequestError("This request_id has already been finalized.")
                wallet = db.execute("SELECT * FROM exchange_wallets WHERE user_id=?", (user_id,)).fetchone()
                pending_free = db.execute(
                    "SELECT COUNT(*) AS n FROM exchange_reservations WHERE user_id=? AND status='pending' AND payment_kind='free'",
                    (user_id,),
                ).fetchone()["n"]
                if wallet["free_remaining"] - pending_free > 0:
                    kind, amount = "free", 0
                else:
                    if wallet["balance_cents"] < self.exchange_price_cents:
                        raise InsufficientCreditsError("Five free exchanges have been used; add credits to continue.")
                    kind, amount = "credit", self.exchange_price_cents
                    db.execute(
                        "UPDATE exchange_wallets SET balance_cents=balance_cents-? WHERE user_id=?",
                        (amount, user_id),
                    )
                reservation_id = __import__("uuid").uuid4().hex
                db.execute(
                    "INSERT INTO exchange_reservations(reservation_id,user_id,request_id,payment_kind,amount_cents,status,created_at) VALUES(?,?,?,?,?,'pending',?)",
                    (reservation_id, user_id, request_id, kind, amount, datetime.now(timezone.utc).isoformat()),
                )
                db.execute("COMMIT")
                return ExchangeReservation(reservation_id, user_id, request_id, kind)
            except Exception:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
            finally:
                db.close()

    def complete_exchange(self, user_id: str, reservation_id: str) -> None:
        user_id = self._user(user_id)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM exchange_reservations WHERE reservation_id=? AND user_id=?",
                (reservation_id, user_id),
            ).fetchone()
            if row is None or row["status"] != "pending":
                db.execute("ROLLBACK")
                raise ExchangeBillingError("Pending exchange reservation not found.")
            if row["payment_kind"] == "free":
                db.execute(
                    "UPDATE exchange_wallets SET free_remaining=free_remaining-1 WHERE user_id=? AND free_remaining>0",
                    (user_id,),
                )
                if db.execute("SELECT changes()").fetchone()[0] != 1:
                    db.execute("ROLLBACK")
                    raise ExchangeBillingError("Free exchange allowance could not be consumed.")
            db.execute("UPDATE exchange_reservations SET status='completed' WHERE reservation_id=?", (reservation_id,))
            db.execute("COMMIT")

    def fail_exchange(self, user_id: str, reservation_id: str) -> None:
        """Release a reservation if the provider fails before a reply is delivered."""
        user_id = self._user(user_id)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM exchange_reservations WHERE reservation_id=? AND user_id=?",
                (reservation_id, user_id),
            ).fetchone()
            if row is None or row["status"] != "pending":
                db.execute("ROLLBACK")
                raise ExchangeBillingError("Pending exchange reservation not found.")
            if row["payment_kind"] == "credit":
                db.execute(
                    "UPDATE exchange_wallets SET balance_cents=balance_cents+? WHERE user_id=?",
                    (row["amount_cents"], user_id),
                )
            db.execute("UPDATE exchange_reservations SET status='failed' WHERE reservation_id=?", (reservation_id,))
            db.execute("COMMIT")

    def credit_wallet(self, user_id: str, amount_cents: int, *, verified_payment_event_id: str) -> bool:
        """Apply a verified Stripe payment once. Returns False for duplicate event IDs.

        Call only after server-side Stripe webhook signature and payment validation.
        """
        user_id = self._user(user_id)
        if not isinstance(amount_cents, int) or isinstance(amount_cents, bool) or amount_cents < 1:
            raise ValueError("amount_cents must be a positive integer.")
        if not isinstance(verified_payment_event_id, str) or not verified_payment_event_id.strip():
            raise ValueError("A verified Stripe event ID is required.")
        event_id = verified_payment_event_id.strip()
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._ensure_wallet(db, user_id)
            try:
                db.execute(
                    "INSERT INTO exchange_topups(payment_event_id,user_id,amount_cents,created_at) VALUES(?,?,?,?)",
                    (event_id, user_id, amount_cents, datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                return False
            db.execute(
                "UPDATE exchange_wallets SET balance_cents=balance_cents+? WHERE user_id=?",
                (amount_cents, user_id),
            )
            db.execute("COMMIT")
            return True

    def get_wallet(self, user_id: str) -> Wallet:
        user_id = self._user(user_id)
        with self._connect() as db:
            self._ensure_wallet(db, user_id)
            row = db.execute("SELECT * FROM exchange_wallets WHERE user_id=?", (user_id,)).fetchone()
        return Wallet(user_id, row["free_remaining"], row["balance_cents"])
