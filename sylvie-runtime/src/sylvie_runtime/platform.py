from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlatformAccessError(PermissionError):
    """Raised when a customer principal lacks a required product permission."""


class Product(str, Enum):
    SYLVIE = "sylvie"
    DIALOGUE_GATEWAY = "dialogue_gateway"
    DIAGNOSTICS_REPAIR = "diagnostics_repair"


@dataclass(frozen=True)
class CustomerPrincipal:
    """Identity claims populated only after upstream server-side token verification.

    Never construct this object from request-body fields or unverified JWT claims.
    """
    customer_id: str
    subject: str
    issuer: str
    scopes: frozenset[str]

    def __post_init__(self) -> None:
        for name, value in (("customer_id", self.customer_id), ("subject", self.subject), ("issuer", self.issuer)):
            if not isinstance(value, str) or not value.strip() or len(value) > 255:
                raise ValueError(f"{name} must be a non-empty string of at most 255 characters.")
        if not isinstance(self.scopes, frozenset) or any(not isinstance(scope, str) or not scope.strip() for scope in self.scopes):
            raise ValueError("scopes must be a frozenset of non-empty strings.")


PRODUCT_SCOPES = {
    Product.SYLVIE: "product:sylvie:use",
    Product.DIALOGUE_GATEWAY: "product:dialogue_gateway:use",
    Product.DIAGNOSTICS_REPAIR: "product:diagnostics_repair:use",
}


def require_product_access(principal: CustomerPrincipal, product: Product) -> None:
    """Enforce a product-specific entitlement after identity verification."""
    if not isinstance(principal, CustomerPrincipal):
        raise PlatformAccessError("A verified customer principal is required.")
    if PRODUCT_SCOPES[product] not in principal.scopes:
        raise PlatformAccessError(f"Customer is not authorized to access {product.value}.")


def require_service_scope(principal: CustomerPrincipal, scope: str) -> None:
    """Enforce a fine-grained permission for a cross-product service call."""
    if not isinstance(principal, CustomerPrincipal):
        raise PlatformAccessError("A verified customer principal is required.")
    if scope not in principal.scopes:
        raise PlatformAccessError("The requested service permission was not granted.")
