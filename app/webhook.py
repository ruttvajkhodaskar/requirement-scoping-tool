import hashlib
import hmac
import json
import logging
import time

import httpx

from app import config

log = logging.getLogger("scoping.webhook")


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_to_crm(payload: dict, attempts: int = 3) -> str:
    """POST the notes to a CRM webhook with retries and an optional HMAC signature.

    The receiver can check the X-Signature header (SHA-256 HMAC of the raw body)
    to confirm the message really came from this service.
    """
    url = config.get("CRM_WEBHOOK_URL")
    if not url:
        return "skipped (CRM_WEBHOOK_URL not set)"

    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    secret = config.get("CRM_WEBHOOK_SECRET")
    if secret:
        headers["X-Signature"] = sign(body, secret)

    last = "unknown error"
    for i in range(attempts):
        try:
            r = httpx.post(url, content=body, headers=headers, timeout=10)
            if r.status_code < 400:
                return f"sent ({r.status_code})"
            last = f"HTTP {r.status_code}"
            if r.status_code < 500:  # client error: retrying will not help
                break
        except httpx.HTTPError as e:
            last = type(e).__name__
        log.warning("CRM webhook attempt %d/%d failed: %s", i + 1, attempts, last)
        if i < attempts - 1:
            time.sleep(0.5 * (2 ** i))
    return f"failed ({last})"
