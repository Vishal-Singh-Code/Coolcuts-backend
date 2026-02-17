import sib_api_v3_sdk
from django.conf import settings
from sib_api_v3_sdk.rest import ApiException
import logging

logger = logging.getLogger(__name__)

def send_otp_email(email: str, otp: int):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email}],
            subject="CoolCuts OTP Verification",
            html_content=f"<p>Your OTP is <strong>{otp}</strong></p>",
            sender={"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
        )
    
        api_instance.send_transac_email(send_smtp_email)

    except ApiException as e:
        logger.error(f"Brevo email failed: {e}")
        raise

