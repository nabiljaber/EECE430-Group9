import os
import jwt
from types import SimpleNamespace
from django.utils.deprecation import MiddlewareMixin


class GatewayJWTMiddleware(MiddlewareMixin):
    """
    Decode auth_token cookie (JWT from accounts service) and attach a lightweight user object.
    Keeps Django's request.user contract by setting a stub with is_authenticated flag.
    """

    def process_request(self, request):
        token = request.COOKIES.get("auth_token")
        if not token:
            return
        secret = os.getenv("ACCOUNTS_JWT_SECRET")
        alg = os.getenv("ACCOUNTS_JWT_ALG", "HS256")
        if not secret:
            return
        try:
            payload = jwt.decode(token, secret, algorithms=[alg])
        except Exception:
            return
        is_dealer_claim = payload.get("is_dealer", False)
        cookie_dealer = request.COOKIES.get("is_dealer", "").lower() in {"true", "1", "yes", "on"}
        user = SimpleNamespace(
            id=payload.get("user_id") or payload.get("sub"),
            username=payload.get("username"),
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            is_dealer=is_dealer_claim or cookie_dealer,
            is_authenticated=True,
        )
        if user.is_dealer:
            user.dealer_profile = SimpleNamespace(active=True)
        request.user = user
        request.auth_claims = payload
