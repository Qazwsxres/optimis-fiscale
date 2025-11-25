from datetime import date
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


# -------------------------------
#  NEW: GET /overdue
#  Returns list of overdue invoices
# -------------------------------
@router.get("/")
def get_overdue_list():
    today = date.today()

    with SessionLocal() as db:
        # Sales overdue (client invoices)
        sales = (
            db.query(InvoiceSale)
            .filter(InvoiceSale.status != "paid")
            .filter(InvoiceSale.due_date < today)
            .all()
        )

        clients = []
        for inv in sales:
            days_late = (today - inv.due_date).days
            clients.append({
                "id": inv.id,
                "number": inv.number,
                "due_date": str(inv.due_date),
                "days_overdue": days_late,
                "amount": float(inv.amount or 0),
                "type": "sale"
            })

        # Purchase overdue (supplier invoices)
        purchases = (
            db.query(InvoicePurchase)
            .filter(InvoicePurchase.status != "paid")
            .filter(InvoicePurchase.due_date < today)
            .all()
        )

        suppliers = []
        for inv in purchases:
            days_late = (today - inv.due_date).days
            suppliers.append({
                "id": inv.id,
                "number": inv.number,
                "due_date": str(inv.due_date),
                "days_overdue": days_late,
                "amount": float(inv.amount or 0),
                "type": "purchase"
            })

        return JSONResponse(
            content={
                "clients_overdue": clients,
                "suppliers_overdue": suppliers,
                "counts": {
                    "clients": len(clients),
                    "suppliers": len(suppliers),
                }
            },
            headers=CORS_HEADERS
        )


# -------------------------------
#  POST /overdue/check
#  Create alerts for overdue invoices
# -------------------------------
@router.post("/check")
def check_overdue_invoices():
    today = date.today()

    with SessionLocal() as db:
        created = 0
        skipped = 0

        overdue_sales = (
            db.query(InvoiceSale)
            .filter(InvoiceSale.status != "paid")
            .filter(InvoiceSale.due_date < today)
            .all()
        )

        overdue_purchases = (
            db.query(InvoicePurchase)
            .filter(InvoicePurchase.status != "paid")
            .filter(InvoicePurchase.due_date < today)
            .all()
        )

        def ensure_alert(alert_type: str, inv, is_sale: bool):
            nonlocal created, skipped

            exists = (
                db.query(Alert)
                .filter(Alert.type == alert_type)
                .filter(Alert.related_id == inv.id)
                .filter(Alert.status == "pending")
                .first()
            )

            if exists:
                skipped += 1
                return

            amount = float(inv.amount or 0)

            msg = (
                f"Facture client en retard: {inv.number} – {amount:.2f} €"
                if is_sale else
                f"Facture fournisseur en retard: {inv.number} – {amount:.2f} €"
            )

            alert = Alert(
                type=alert_type,
                related_id=inv.id,
                message=msg,
                due_date=inv.due_date,
                status="pending",
            )
            db.add(alert)
            created += 1

        for inv in overdue_sales:
            ensure_alert("overdue_sale", inv, True)

        for inv in overdue_purchases:
            ensure_alert("overdue_purchase", inv, False)

        db.commit()

        return JSONResponse(
            content={
                "today": str(today),
                "overdue_sales": len(overdue_sales),
                "overdue_purchases": len(overdue_purchases),
                "alerts_created": created,
                "alerts_skipped_existing": skipped,
            },
            headers=CORS_HEADERS
        )


@router.options("/{path:path}")
def overdue_options(path: str):
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)
