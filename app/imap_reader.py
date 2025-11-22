import os
import imaplib
import email
import csv
import io
from datetime import datetime

from .database import SessionLocal
from .models_extended import InvoiceSale, InvoicePurchase

# Outlook / Office365 defaults
IMAP_HOST = os.getenv("IMAP_HOST", "outlook.office365.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")


def _parse_date(value: str):
    """
    Very simple date parser for invoice CSV.
    Tries common formats, returns datetime.date or None if it fails.
    """
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(v, default=0.0):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return default


def _connect_imap():
    if not IMAP_USER or not IMAP_PASSWORD:
        raise RuntimeError("IMAP_USER / IMAP_PASSWORD not configured")

    m = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    m.login(IMAP_USER, IMAP_PASSWORD)
    m.select(IMAP_FOLDER)
    return m


def _process_invoice_csv(text: str):
    """
    Process one CSV attachment as 'invoices' file.

    Expected columns (best-effort):
      - number
      - issue_date
      - due_date
      - amount
      - vat (optional)
      - type (optional: 'sale' or 'purchase')

    If 'type' is missing, we default to 'sale'.
    """
    created_sales = 0
    created_purchases = 0

    reader = csv.DictReader(io.StringIO(text))
    with SessionLocal() as db:
        for row in reader:
            number = (row.get("number") or row.get("invoice_number") or "").strip()
            if not number:
                continue

            issue_date = _parse_date(row.get("issue_date") or row.get("date") or "")
            due_date = _parse_date(row.get("due_date") or "")
            amount = _safe_float(row.get("amount"))
            vat = _safe_float(row.get("vat") or 0)

            inv_type = (row.get("type") or "sale").strip().lower()

            if inv_type.startswith("purch"):
                # Purchase invoice
                obj = InvoicePurchase(
                    number=number,
                    issue_date=issue_date,
                    due_date=due_date,
                    amount=amount,
                    vat=vat,
                    status="pending",
                )
                db.add(obj)
                created_purchases += 1
            else:
                # Sales invoice (default)
                obj = InvoiceSale(
                    number=number,
                    issue_date=issue_date,
                    due_date=due_date,
                    amount=amount,
                    vat=vat,
                    status="draft",
                )
                db.add(obj)
                created_sales += 1

        db.commit()

    return created_sales, created_purchases


def fetch_invoices_from_imap():
    """
    Connect to Outlook IMAP, scan UNSEEN emails, extract .csv attachments
    and create sales / purchase invoices from them.

    Returns a summary dict:
      {
        "ok": True,
        "processed_messages": N,
        "files": number_of_csv_files,
        "sales_created": X,
        "purchases_created": Y,
      }
    """
    m = _connect_imap()

    # Search for UNSEEN emails in the selected folder
    typ, data = m.search(None, "UNSEEN")
    if typ != "OK":
        m.logout()
        return {
            "ok": False,
            "processed_messages": 0,
            "files": 0,
            "sales_created": 0,
            "purchases_created": 0,
            "detail": f"IMAP search error: {typ}",
        }

    msg_ids = data[0].split()
    total_sales = 0
    total_purchases = 0
    file_count = 0

    for msg_id in msg_ids:
        typ, msg_data = m.fetch(msg_id, "(RFC822)")
        if typ != "OK" or not msg_data:
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Walk through all parts to find attachments
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition") or "")

            if "attachment" not in content_disposition.lower():
                continue

            filename = part.get_filename()
            if not filename:
                continue

            # Only CSV for now
            if not filename.lower().endswith(".csv"):
                continue

            file_bytes = part.get_payload(decode=True) or b""
            try:
                text = file_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue

            s, p = _process_invoice_csv(text)
            total_sales += s
            total_purchases += p
            file_count += 1

        # Mark email as seen
        m.store(msg_id, "+FLAGS", "\\Seen")

    m.close()
    m.logout()

    return {
        "ok": True,
        "processed_messages": len(msg_ids),
        "files": file_count,
        "sales_created": total_sales,
        "purchases_created": total_purchases,
    }
