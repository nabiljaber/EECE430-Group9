from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import status
import json

User = get_user_model()


def _token_response(user):
    refresh = RefreshToken.for_user(user)
    refresh["username"] = user.username
    refresh["email"] = user.email
    refresh["first_name"] = user.first_name
    refresh["last_name"] = user.last_name
    refresh["is_dealer"] = getattr(user, "dealer_profile", None) is not None
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            # Dealer status is owned by rentals service; include hint flag if present
            "is_dealer": getattr(user, "dealer_profile", None) is not None,
        },
        "token": str(refresh.access_token),
        "refresh": str(refresh),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    try:
        data = request.data
        required = ["username", "password", "email"]
        if any(k not in data or not data[k] for k in required):
            return JsonResponse({"detail": "Missing required fields."}, status=400)
        if User.objects.filter(username__iexact=data["username"]).exists():
            return JsonResponse({"detail": "Username already taken."}, status=400)
        if User.objects.filter(email__iexact=data["email"]).exists():
            return JsonResponse({"detail": "Email already in use."}, status=400)
        try:
            validate_password(data["password"])
        except ValidationError as e:
            return JsonResponse({"detail": " ".join(e.messages)}, status=400)
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
        return JsonResponse(_token_response(user), status=201)
    except Exception as exc:
        return JsonResponse({"detail": "Server error", "error": str(exc)}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({"detail": "Invalid credentials."}, status=401)
    return JsonResponse(_token_response(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_view(request):
    refresh = request.data.get("refresh")
    if not refresh:
        return JsonResponse({"detail": "Refresh token required."}, status=400)
    try:
        token = RefreshToken(refresh)
        access = token.access_token
        return JsonResponse({"token": str(access)})
    except Exception:
        return JsonResponse({"detail": "Invalid refresh token."}, status=401)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    u = request.user
    return JsonResponse(
        {
            "user": {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_dealer": getattr(u, "dealer_profile", None) is not None,
            }
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    # Stateless JWT logout: caller should drop the token; we still accept to keep contract
    return JsonResponse({"detail": "Logged out."})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def user_update(request):
    u = request.user
    updated_fields = []
    for field in ["first_name", "last_name", "email"]:
        if field in request.data:
            setattr(u, field, request.data[field])
            updated_fields.append(field)
    if updated_fields:
        u.save(update_fields=updated_fields)
    return JsonResponse(
        {
            "user": {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_dealer": getattr(u, "dealer_profile", None) is not None,
            }
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    # Placeholder: in a real deployment, send email with token
    email = request.data.get("email")
    if not email:
        return JsonResponse({"detail": "Email required."}, status=400)
    exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse(
        {"detail": "If an account exists, a reset link will be sent.", "found": exists}
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    # Placeholder to complete contract without wiring email tokens yet
    return JsonResponse({"detail": "Not implemented in this stub."}, status=status.HTTP_501_NOT_IMPLEMENTED)
