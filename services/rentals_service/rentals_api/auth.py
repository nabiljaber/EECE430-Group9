import os
import jwt
from django.utils.functional import SimpleLazyObject
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from types import SimpleNamespace
from django.conf import settings


class ServiceJWTAuthentication(BaseAuthentication):
    """
    Minimal JWT auth that trusts tokens issued by the Accounts service.
    Expects Authorization: Bearer <token>
    """

    def authenticate(self, request):
        auth = request.headers.get("Authorization") or ""
        if not auth.lower().startswith("bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(
                token,
                settings.ACCOUNTS_JWT_SECRET,
                algorithms=[settings.ACCOUNTS_JWT_ALGORITHM],
            )
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid token")
        user = SimpleNamespace(
            id=payload.get("user_id") or payload.get("sub"),
            username=payload.get("username"),
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            is_dealer=payload.get("is_dealer", False),
            is_authenticated=True,
        )
        request.user_id = user.id
        return (user, None)
