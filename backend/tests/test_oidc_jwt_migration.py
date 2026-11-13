"""Regression test for the python-jose -> PyJWT OIDC id_token verification.

PyJWT's ``jwt.decode`` rejects a bare JWK dict (it expects a parsed key object
or a PEM/JSON string), whereas python-jose accepted dicts. Passing the raw JWK
dict raised ``Expecting a PEM-formatted key.`` and broke every OIDC login with a
401 "Invalid OIDC token" (see backend/app/domain/auth/sso.py::exchange_oidc_code).
This exercises the full ``exchange_oidc_code`` path with a real RSA-signed
id_token and a JWKS that contains the matching public key.
"""

import base64

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domain.auth.sso import OIDCProvider, exchange_oidc_code


def _b64url_uint(n: int) -> str:
    payload = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _make_provider() -> OIDCProvider:
    return OIDCProvider(
        key="entra",
        display_name="Entra",
        issuer="https://login.microsoftonline.com/tenant/v2.0",
        client_id="app-client-id",
        client_secret="secret",
        authorization_endpoint="https://login.microsoftonline.com/tenant/oauth2/v2.0/authorize",
        token_endpoint="https://example.invalid/token",
        jwks_uri="https://example.invalid/keys",
        scopes="openid profile email",
        group_claim="groups",
        email_claim="email",
        name_claim="name",
        subject_claim="sub",
        allow_auto_create=False,
        enabled=True,
    )


def test_exchange_oidc_code_verifies_jwk_dict(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
        "kid": "signing-key-1",
        "alg": "RS256",
        "use": "sig",
    }

    id_token = pyjwt.encode(
        {
            "sub": "user-subject",
            "iss": "https://login.microsoftonline.com/tenant/v2.0",
            "aud": "app-client-id",
            "exp": 9999999999,
            "email": "sso@example.com",
            "name": "SSO User",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "signing-key-1"},
    )

    monkeypatch.setattr(
        "app.domain.auth.sso._form_http",
        lambda url, payload: {"id_token": id_token},
    )
    monkeypatch.setattr(
        "app.domain.auth.sso._json_http",
        lambda method, url, payload=None: {"keys": [jwk]},
    )

    claims = exchange_oidc_code(_make_provider(), "auth-code", "http://localhost/login")
    assert claims["sub"] == "user-subject"
    assert claims["email"] == "sso@example.com"
