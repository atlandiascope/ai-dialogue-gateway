import pytest

from sylvie_runtime.platform import CustomerPrincipal, PlatformAccessError, Product, require_product_access, require_service_scope


def principal(*scopes):
    return CustomerPrincipal("cus_internal_123", "identity-provider|subject-456", "https://identity.example.test/", frozenset(scopes))


def test_customer_can_access_only_entitled_product():
    user = principal("product:sylvie:use")
    require_product_access(user, Product.SYLVIE)
    with pytest.raises(PlatformAccessError):
        require_product_access(user, Product.DIALOGUE_GATEWAY)


def test_service_calls_require_explicit_scope():
    user = principal("service:gateway:send")
    require_service_scope(user, "service:gateway:send")
    with pytest.raises(PlatformAccessError):
        require_service_scope(user, "service:repair:execute")


def test_principal_rejects_invalid_identity_fields():
    with pytest.raises(ValueError):
        CustomerPrincipal("", "subject", "issuer", frozenset())
    with pytest.raises(ValueError):
        CustomerPrincipal("customer", "subject", "issuer", {"product:sylvie:use"})
