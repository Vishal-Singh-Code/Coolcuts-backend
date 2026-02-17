import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

from user.models import EmailOTP
from user.utils.email import send_otp_email

OTP_EXPIRY = 300  # 5 minutes
MAX_OTP_ATTEMPTS = 5


def normalize_email(email: str) -> str:
    return str(email).strip().lower()


def generate_and_send_otp(email: str):
    email = normalize_email(email)
    otp = f"{secrets.randbelow(1000000):06d}"
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    EmailOTP.objects.update_or_create(
        email=email,
        defaults={
            "otp_hash": otp_hash,
            "attempts": 0,
            "expires_at": timezone.now() + timedelta(seconds=OTP_EXPIRY),
        },
    )
    send_otp_email(email, otp)


def verify_otp(email: str, otp: str):
    email = normalize_email(email)
    try:
        otp_record = EmailOTP.objects.get(email=email)
    except EmailOTP.DoesNotExist:
        return False, "not_found"

    if otp_record.is_expired:
        otp_record.delete()
        return False, "expired"

    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        return False, "too_many_attempts"

    otp_hash = hashlib.sha256(str(otp).encode()).hexdigest()
    if otp_hash == otp_record.otp_hash:
        otp_record.delete()
        return True, "verified"

    otp_record.attempts += 1
    otp_record.save(update_fields=["attempts", "updated_at"])
    return False, "invalid"


def clear_otp(email: str):
    email = normalize_email(email)
    EmailOTP.objects.filter(email=email).delete()
