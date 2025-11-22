from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os

from ..imap_reader import fetch_invoices_from_imap

router = APIRouter(prefix="/email", tags=["Email"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}

# Optional simple protection via token
EMAIL_IMPORT_TOKEN = os.getenv("EMAIL_IMPORT_TOKEN")


@router.post("/pull")
def pull_email_invoices(token: str | None = None):
    """
    Manually trigger import of invoices from Outlook IMAP.

    POST /email/pull?token=YOUR_SECRET   (if EMAIL_IMPORT_TOKEN is set)
    or just POST /email/pull             (if no token configured)
    """
    if EMAIL_IMPORT_TOKEN:
        if token != EMAIL_IMPORT_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")

    try:
        summary = fetch_invoices_from_imap()
        return JSONResponse(content=summary, headers=CORS_HEADERS)
    except RuntimeError as e:
        # IMAP not configured or similar
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IMAP import error: {e}")


@router.options("/{path:path}")
def email_options():
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)
