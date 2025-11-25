from datetime import date, timedelta

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase, Alert

router = APIRouter(prefix="/overdue", tags=["Overdue"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}


@router.post("/check")
def check_overdue_invoices():
    """
    Scan all sales & purchase invoices and create alerts
    for those that are overdue and not paid.

    - Sales:   type = "overdue_sale"
    - Purchases: type = "overdue_purchase"
    """
    today = date.today()

    with SessionLocal() as db:
        created = 0
        skipped = 0

        # 1) Overdue sales (client invoices)
        overdue_sales = (
            db.query(InvoiceSale)
            .filter(InvoiceSale.status != "paid")
            .filter(InvoiceSale.due_date < today)
            .all()
        )

        # 2) Overdue purchases (supplier invoices)
        overdue_purchases = (
            db.query(InvoicePurchase)
            .filter(InvoicePurchase.status != "paid")
            .filter(InvoicePurchase.due_date < today)
            .all()
        )

        def ensure_alert(alert_type: str, inv, is_sale: bool):
            nonlocal created, skipped

            # Avoid duplicates for same invoice
            existing = (
                db.query(Alert)
                .filter(Alert.type == alert_type)
                .filter(Alert.related_id == inv.id)
                .filter(Alert.status == "pending")
                .first()
            )
            if existing:
                skipped += 1
                return

            amount = float(inv.amount) if inv.amount is not None else 0.0
            if is_sale:
                msg = f"Facture client en retard: {inv.number} – {amount:.2f} €"
            else:
                msg = f"Facture fournisseur en retard: {inv.number} – {amount:.2f} €"

            alert = Alert(
                type=alert_type,
                related_id=inv.id,
                message=msg,
                due_date=inv.due_date,
                status="pending",
            )
            db.add(alert)
            created += 1

        # Create alerts for each overdue invoice
        for inv in overdue_sales:
            ensure_alert("overdue_sale", inv, is_sale=True)

        for inv in overdue_purchases:
            ensure_alert("overdue_purchase", inv, is_sale=False)

        db.commit()

        payload = {
            "today": str(today),
            "overdue_sales": len(overdue_sales),
            "overdue_purchases": len(overdue_purchases),
            "alerts_created": created,
            "alerts_skipped_existing": skipped,
        }
        return JSONResponse(content=payload, headers=CORS_HEADERS)


@router.options("/{path:path}")
def overdue_options(path: str):
    """
    CORS preflight support if you ever call this from the browser.
    """
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)
