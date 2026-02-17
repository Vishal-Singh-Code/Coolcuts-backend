import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from user.models import EmailOTP


class RegistrationOTPTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.email_patcher = patch("user.services.otp_service.send_otp_email")
        self.mock_send_email = self.email_patcher.start()

        self.send_otp_url = reverse("send-otp")
        self.register_url = reverse("verify-otp-and-register")

        self.email = "testuser@gmail.com"
        self.password = "Strong@123"
        self.otp = "123456"

        otp_hash = hashlib.sha256(self.otp.encode()).hexdigest()
        EmailOTP.objects.create(
            email=self.email,
            otp_hash=otp_hash,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def tearDown(self):
        self.email_patcher.stop()
        EmailOTP.objects.all().delete()

    def test_send_otp_success(self):
        response = self.client.post(self.send_otp_url, {"email": self.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data.get("otp_expires_in"), 300)
        self.mock_send_email.assert_called_once()

    def test_send_otp_existing_user_returns_generic_success(self):
        User.objects.create_user(username=self.email, email=self.email, password=self.password)
        response = self.client.post(self.send_otp_url, {"email": self.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_register_with_valid_otp(self):
        response = self.client.post(
            self.register_url,
            {"email": self.email, "otp": self.otp, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username=self.email).exists())
        user = User.objects.get(username=self.email)
        self.assertTrue(user.profile.is_verified)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], self.email)
        self.assertEqual(response.data["user"]["is_staff"], user.is_staff)

    def test_register_with_invalid_otp(self):
        response = self.client.post(
            self.register_url,
            {"email": self.email, "otp": "000000", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username=self.email).exists())

    def test_register_with_weak_password(self):
        response = self.client.post(
            self.register_url,
            {"email": self.email, "otp": self.otp, "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username=self.email).exists())

    def test_register_duplicate_user(self):
        User.objects.create_user(username=self.email, email=self.email, password=self.password)
        response = self.client.post(
            self.register_url,
            {"email": self.email, "otp": self.otp, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="first@example.com",
            email="duplicate@example.com",
            password=self.password,
        )
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="second@example.com",
                email="duplicate@example.com",
                password=self.password,
            )

    def test_register_fails_after_max_otp_attempts(self):
        otp_row = EmailOTP.objects.get(email=self.email)
        otp_row.attempts = 5
        otp_row.save(update_fields=["attempts"])

        response = self.client.post(
            self.register_url,
            {"email": self.email, "otp": self.otp, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data.get("error"),
            "Too many invalid attempts. Please request a new OTP.",
        )


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("login")
        self.email = "testuser@gmail.com"
        self.password = "Strong@123"

        self.user = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
        )
        self.user.profile.is_verified = True
        self.user.profile.save()

    def test_login_success(self):
        response = self.client.post(
            self.login_url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], self.email)
        self.assertEqual(response.data["user"]["is_staff"], self.user.is_staff)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.login_url,
            {"email": self.email, "password": "WrongPassword123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_unverified_user(self):
        self.user.profile.is_verified = False
        self.user.profile.save()

        response = self.client.post(
            self.login_url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_non_existent_user(self):
        response = self.client.post(
            self.login_url,
            {"email": "nouser@gmail.com", "password": "Random@123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ForgotPasswordTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.email_patcher = patch("user.services.otp_service.send_otp_email")
        self.mock_send_email = self.email_patcher.start()

        self.send_otp_url = reverse("forgot-password-send-otp")
        self.reset_url = reverse("forgot-password-reset")

        self.email = "testuser@gmail.com"
        self.old_password = "Strong@123"
        self.new_password = "NewStrong@123"
        self.otp = "123456"

        self.user = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.old_password,
        )

    def tearDown(self):
        self.email_patcher.stop()
        EmailOTP.objects.all().delete()

    def _create_otp(self, email=None, attempts=0):
        otp_hash = hashlib.sha256(self.otp.encode()).hexdigest()
        EmailOTP.objects.update_or_create(
            email=email or self.email,
            defaults={
                "otp_hash": otp_hash,
                "attempts": attempts,
                "expires_at": timezone.now() + timedelta(minutes=5),
            },
        )

    def test_forgot_password_send_otp_for_existing_user(self):
        response = self.client.post(self.send_otp_url, {"email": self.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data.get("otp_expires_in"), 300)
        self.mock_send_email.assert_called_once()

    def test_forgot_password_send_otp_for_non_existing_user(self):
        response = self.client.post(self.send_otp_url, {"email": "nouser@gmail.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.mock_send_email.assert_not_called()

    def test_forgot_password_reset_with_valid_otp(self):
        self._create_otp()

        response = self.client.post(
            self.reset_url,
            {"email": self.email, "otp": self.otp, "password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(EmailOTP.objects.filter(email=self.email).exists())

    def test_forgot_password_reset_with_invalid_otp(self):
        self._create_otp()

        response = self.client.post(
            self.reset_url,
            {"email": self.email, "otp": "000000", "password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.old_password))

    def test_forgot_password_reset_fails_after_max_otp_attempts(self):
        self._create_otp(attempts=5)

        response = self.client.post(
            self.reset_url,
            {"email": self.email, "otp": self.otp, "password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data.get("error"),
            "Too many invalid attempts. Please request a new OTP.",
        )

    def test_forgot_password_reset_non_existing_user(self):
        response = self.client.post(
            self.reset_url,
            {"email": "nouser@gmail.com", "otp": self.otp, "password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoogleAuthTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.google_url = reverse("google-auth")

    @override_settings(GOOGLE_CLIENT_ID="google-client-id.apps.googleusercontent.com")
    @patch("user.views.verify_google_id_token")
    def test_google_auth_creates_user_and_returns_tokens(self, mock_verify):
        mock_verify.return_value = {
            "email": "googleuser@gmail.com",
            "given_name": "Google",
            "family_name": "User",
            "name": "Google User",
        }

        response = self.client.post(
            self.google_url,
            {"id_token": "valid-google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        user = User.objects.get(username="googleuser@gmail.com")
        self.assertEqual(user.email, "googleuser@gmail.com")
        self.assertTrue(user.profile.is_verified)
        self.assertEqual(user.profile.name, "Google User")

    @override_settings(GOOGLE_CLIENT_ID="google-client-id.apps.googleusercontent.com")
    @patch("user.views.verify_google_id_token")
    def test_google_auth_invalid_token(self, mock_verify):
        from user.services.google_auth_service import GoogleTokenVerificationError

        mock_verify.side_effect = GoogleTokenVerificationError("invalid")
        response = self.client.post(
            self.google_url,
            {"id_token": "invalid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid Google token", response.data.get("error", ""))
