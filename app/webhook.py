import os
import httpx


def send_to_crm(payload: dict) -> str:
    """POST the scoping notes to a CRM webhook. Skipped if no URL is set."""
    url = os.getenv("CRM_WEBHOOK_URL")
    if not url:
        return "skipped (CRM_WEBHOOK_URL not set)"
    try:
        r = httpx.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return f"sent ({r.status_code})"
    except httpx.HTTPError as e:
        return f"failed ({e})"
