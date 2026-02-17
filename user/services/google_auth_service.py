import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleTokenVerificationError(Exception):
    def __init__(self, message: str, code: str = "verification_failed"):
        super().__init__(message)
        self.code = code


def verify_google_id_token(id_token: str, expected_client_id: str) -> dict:
    query = urlencode({"id_token": id_token})
    url = f"{GOOGLE_TOKENINFO_URL}?{query}"

    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GoogleTokenVerificationError("Unable to verify Google token", code="tokeninfo_request_failed") from exc

    if payload.get("aud") != expected_client_id:
        raise GoogleTokenVerificationError("Google token audience mismatch", code="audience_mismatch")

    if payload.get("email_verified") != "true":
        raise GoogleTokenVerificationError("Google email is not verified", code="email_not_verified")

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise GoogleTokenVerificationError("Google token does not include email", code="missing_email")

    return {
        "email": email,
        "given_name": str(payload.get("given_name", "")).strip(),
        "family_name": str(payload.get("family_name", "")).strip(),
        "name": str(payload.get("name", "")).strip(),
    }
