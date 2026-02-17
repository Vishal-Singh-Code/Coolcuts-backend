from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class EmailNormalizeMixin:
    def validate_email(self, value):
        return value.strip().lower()


class SendOTPSerializer(EmailNormalizeMixin, serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPRegisterSerializer(EmailNormalizeMixin, serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.RegexField(r"^\d{6}$")
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(EmailNormalizeMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordRequestSerializer(EmailNormalizeMixin, serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordConfirmSerializer(EmailNormalizeMixin, serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.RegexField(r"^\d{6}$")
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()

