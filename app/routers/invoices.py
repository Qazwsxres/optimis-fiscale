# ---------- SALES INVOICES ----------

@router.post("/invoices/sales")
async def upload_sales_invoices(file: UploadFile = File(...)):
    """
    Upload sales invoices (CSV/XLSX).
    Front-end: uploadGeneric('salesFile','/invoices/sales',...)
    Here we implement CSV only for simplicity.
    """
    global _sales_invoices
    _sales_invoices = []

    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(status_code=400, detail="File must be CSV for now")

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        for row in reader:
            inv = {
                "number": row.get("number") or row.get("invoice_number") or "",
                "issue_date": row.get("date") or row.get("issue_date") or "",
                "due_date": row.get("due_date") or "",
                "amount": float(str(row.get("amount") or row.get("total") or "0").replace(",", ".")),
                "status": row.get("status") or "open",
            }
            _sales_invoices.append(inv)

        return {"ok": True, "count": len(_sales_invoices)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing sales file: {e}")


@router.get("/invoices/sales")
async def get_sales_invoices():
    """
    Used by your front-end dashboard:
    fetch(apiBase+'/invoices/sales')
    Should return an array of objects with: number, issue_date, due_date, amount, status
    """
    return _sales_invoices
