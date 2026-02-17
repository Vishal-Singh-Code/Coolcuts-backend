from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.conf import settings
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ForgotPasswordConfirmSerializer,
    ForgotPasswordRequestSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    SendOTPSerializer,
    VerifyOTPRegisterSerializer,
)
from user.services.google_auth_service import GoogleTokenVerificationError, verify_google_id_token
from user.services.otp_service import OTP_EXPIRY, clear_otp, generate_and_send_otp, verify_otp

logger = logging.getLogger(__name__)


def build_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
    }

# ---------------------------
# REGISTER VIEW (JWT)
# ---------------------------
class SendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Avoid user enumeration: do not disclose whether account exists.
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"message": "If eligible, OTP has been sent successfully", "otp_expires_in": OTP_EXPIRY},
                status=status.HTTP_200_OK
            )

        generate_and_send_otp(email)
        return Response(
            {"message": "If eligible, OTP has been sent successfully", "otp_expires_in": OTP_EXPIRY},
            status=status.HTTP_200_OK
        )


class VerifyOTPAndRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = VerifyOTPRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        password = serializer.validated_data["password"]

        # Keep error response generic to reduce account enumeration risk.
        if User.objects.filter(email__iexact=email).exists():
            return Response({"error": "Unable to register with provided credentials"}, status=status.HTTP_400_BAD_REQUEST)

        is_valid_otp, otp_reason = verify_otp(email, otp)
        if not is_valid_otp:
            if otp_reason == "too_many_attempts":
                message = "Too many invalid attempts. Please request a new OTP."
            else:
                message = "Invalid or expired OTP"
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                )
        except IntegrityError:
            return Response(
                {"error": "Unable to register with provided credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.profile.is_verified = True
        user.profile.save()

        clear_otp(email)

        # Issue JWT tokens (auto login)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "User registered and logged in successfully",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": build_user_payload(user)
            },
            status=status.HTTP_201_CREATED
        )

# ---------------------------
# LOGIN VIEW (JWT)
# ---------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.profile.is_verified:
            return Response(
                {"error": "Account not verified"},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": build_user_payload(user)
            },
            status=status.HTTP_200_OK
        )


# ---------------------------
# FORGET PASSWORD VIEW
# ---------------------------
class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user_exists = User.objects.filter(email__iexact=email).exists()

        if user_exists:
            generate_and_send_otp(email)

        return Response(
            {"message": "If eligible, OTP has been sent successfully", "otp_expires_in": OTP_EXPIRY},
            status=status.HTTP_200_OK
        )


class ForgotPasswordConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = ForgotPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"error": "Unable to reset password with provided credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_valid_otp, otp_reason = verify_otp(email, otp)
        if not is_valid_otp:
            if otp_reason == "too_many_attempts":
                message = "Too many invalid attempts. Please request a new OTP."
            else:
                message = "Invalid or expired OTP"
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save(update_fields=["password"])
        clear_otp(email)

        return Response(
            {"message": "Password reset successful"},
            status=status.HTTP_200_OK
        )


# ---------------------------
# GOOGLE_AUTH VIEW (JWT)
# ---------------------------
class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "google_auth"

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data["id_token"]

        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {"error": "Google auth is not configured on server"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            google_user = verify_google_id_token(id_token, settings.GOOGLE_CLIENT_ID)
        except GoogleTokenVerificationError as exc:
            logger.warning("Google auth verification failed: %s (%s)", str(exc), getattr(exc, "code", "unknown"))
            message = "Invalid Google token"
            if settings.DEBUG:
                message = f"Invalid Google token: {str(exc)}"
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = google_user["email"]
        first_name = google_user["given_name"]
        last_name = google_user["family_name"]
        full_name = google_user["name"] or " ".join(filter(None, [first_name, last_name])).strip()

        try:
            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email,
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                )
                if created:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
        except IntegrityError:
            return Response(
                {"error": "Unable to login with Google"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = user.profile
        profile.is_verified = True
        if full_name:
            profile.name = full_name
        profile.save(update_fields=["is_verified", "name"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": build_user_payload(user)
            },
            status=status.HTTP_200_OK
        )


# ---------------------------
# LOGOUT VIEW (JWT Blacklist)
# ---------------------------
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "name": profile.name,
            "phone": profile.phone,
        })

    def patch(self, request):
        user = request.user
        profile = user.profile

        name = request.data.get("name")
        phone = request.data.get("phone")

        if name is not None:
            name = str(name).strip()
            if not name:
                return Response({"error": "Name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
            profile.name = name

        if phone is not None:
            phone = str(phone).strip()
            profile.phone = phone

        profile.save()

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "name": profile.name,
            "phone": profile.phone,
        })


