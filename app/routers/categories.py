"""
Categories Router - Transaction Categorization
Hierarchical categories with auto-categorization
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from ..database import SessionLocal
from ..models_banking import Category, BankTransactionEnhanced

router = APIRouter(prefix="/api/categories", tags=["Categories"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# MODELS
# ============================================

class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    type: str = "expense"  # income, expense, transfer, savings
    is_deductible: bool = False
    deduction_rate: Optional[float] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_deductible: Optional[bool] = None
    deduction_rate: Optional[float] = None

# ============================================
# CREATE CATEGORY
# ============================================

@router.post("/", status_code=201)
def create_category(category: CategoryCreate):
    """Create a new category"""
    try:
        with SessionLocal() as db:
            # Verify parent exists if specified
            if category.parent_id:
                parent = db.query(Category).filter(Category.id == category.parent_id).first()
                if not parent:
                    raise HTTPException(404, "Parent category not found")
            
            cat = Category(
                name=category.name,
                parent_id=category.parent_id,
                icon=category.icon,
                color=category.color,
                type=category.type,
                is_system=False,
                is_deductible=category.is_deductible,
                deduction_rate=category.deduction_rate
            )
            
            db.add(cat)
            db.commit()
            db.refresh(cat)
            
            return JSONResponse(
                content={
                    "id": cat.id,
                    "name": cat.name,
                    "parent_id": cat.parent_id,
                    "icon": cat.icon,
                    "color": cat.color,
                    "type": cat.type
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# LIST CATEGORIES
# ============================================

@router.get("/")
def list_categories(type: Optional[str] = None):
    """List all categories, optionally filtered by type"""
    try:
        with SessionLocal() as db:
            query = db.query(Category)
            
            if type:
                query = query.filter(Category.type == type)
            
            categories = query.order_by(Category.name).all()
            
            return JSONResponse(
                content=[{
                    "id": cat.id,
                    "name": cat.name,
                    "parent_id": cat.parent_id,
                    "icon": cat.icon,
                    "color": cat.color,
                    "type": cat.type,
                    "is_system": cat.is_system,
                    "is_deductible": cat.is_deductible,
                    "deduction_rate": float(cat.deduction_rate) if cat.deduction_rate else None
                } for cat in categories],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# GET CATEGORY TREE
# ============================================

@router.get("/tree")
def get_category_tree():
    """Get categories as hierarchical tree"""
    try:
        with SessionLocal() as db:
            categories = db.query(Category).all()
            
            # Build tree structure
            cat_dict = {cat.id: {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "type": cat.type,
                "is_deductible": cat.is_deductible,
                "children": []
            } for cat in categories}
            
            tree = []
            for cat in categories:
                if cat.parent_id and cat.parent_id in cat_dict:
                    cat_dict[cat.parent_id]["children"].append(cat_dict[cat.id])
                elif not cat.parent_id:
                    tree.append(cat_dict[cat.id])
            
            return JSONResponse(
                content=tree,
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# UPDATE CATEGORY
# ============================================

@router.put("/{category_id}")
def update_category(category_id: int, category: CategoryUpdate):
    """Update a category"""
    try:
        with SessionLocal() as db:
            cat = db.query(Category).filter(Category.id == category_id).first()
            
            if not cat:
                raise HTTPException(404, "Category not found")
            
            if cat.is_system:
                raise HTTPException(403, "Cannot modify system categories")
            
            if category.name is not None:
                cat.name = category.name
            if category.icon is not None:
                cat.icon = category.icon
            if category.color is not None:
                cat.color = category.color
            if category.is_deductible is not None:
                cat.is_deductible = category.is_deductible
            if category.deduction_rate is not None:
                cat.deduction_rate = category.deduction_rate
            
            db.commit()
            db.refresh(cat)
            
            return JSONResponse(
                content={
                    "id": cat.id,
                    "name": cat.name,
                    "message": "Category updated"
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# DELETE CATEGORY
# ============================================

@router.delete("/{category_id}")
def delete_category(category_id: int):
    """Delete a category (only if no transactions use it)"""
    try:
        with SessionLocal() as db:
            cat = db.query(Category).filter(Category.id == category_id).first()
            
            if not cat:
                raise HTTPException(404, "Category not found")
            
            if cat.is_system:
                raise HTTPException(403, "Cannot delete system categories")
            
            # Check if used by transactions
            trans_count = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.category_id == category_id)\
                .count()
            
            if trans_count > 0:
                raise HTTPException(400, f"Cannot delete: {trans_count} transactions use this category")
            
            # Check if has children
            children = db.query(Category).filter(Category.parent_id == category_id).count()
            if children > 0:
                raise HTTPException(400, f"Cannot delete: has {children} sub-categories")
            
            db.delete(cat)
            db.commit()
            
            return JSONResponse(
                content={"message": "Category deleted"},
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# AUTO-CATEGORIZE TRANSACTION
# ============================================

@router.post("/auto-categorize/{transaction_id}")
def auto_categorize_transaction(transaction_id: int):
    """
    Automatically categorize a transaction based on label patterns
    
    Simple rule-based categorization:
    - Looks for keywords in transaction label
    - Assigns category with confidence score
    """
    try:
        with SessionLocal() as db:
            trans = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.id == transaction_id)\
                .first()
            
            if not trans:
                raise HTTPException(404, "Transaction not found")
            
            # Define categorization rules
            patterns = {
                "SALAIRE": ("Revenus", "income", 0.95),
                "VIREMENT": ("Transfert", "transfer", 0.80),
                "CARTE": ("Dépenses diverses", "expense", 0.60),
                "UBER": ("Transport", "expense", 0.90),
                "RESTO": ("Alimentation", "expense", 0.85),
                "NETFLIX": ("Abonnements", "expense", 0.95),
                "SPOTIFY": ("Abonnements", "expense", 0.95),
                "AMAZON": ("Shopping", "expense", 0.85),
                "CARREFOUR": ("Alimentation", "expense", 0.90),
                "ESSENCE": ("Transport", "expense", 0.90),
                "LOYER": ("Logement", "expense", 0.95),
                "EDF": ("Énergie", "expense", 0.95),
                "INTERNET": ("Télécoms", "expense", 0.90),
            }
            
            label_upper = (trans.label or "").upper()
            
            for pattern, (cat_name, cat_type, confidence) in patterns.items():
                if pattern in label_upper:
                    # Find or create category
                    category = db.query(Category)\
                        .filter(Category.name == cat_name)\
                        .first()
                    
                    if not category:
                        category = Category(
                            name=cat_name,
                            type=cat_type,
                            is_system=True
                        )
                        db.add(category)
                        db.commit()
                        db.refresh(category)
                    
                    trans.category_id = category.id
                    trans.confidence_score = confidence
                    db.commit()
                    
                    return JSONResponse(
                        content={
                            "transaction_id": transaction_id,
                            "category": cat_name,
                            "confidence": confidence,
                            "message": "Transaction categorized"
                        },
                        headers=get_cors_headers()
                    )
            
            # No pattern matched
            return JSONResponse(
                content={
                    "transaction_id": transaction_id,
                    "category": None,
                    "message": "No category pattern matched"
                },
                headers=get_cors_headers()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# BULK AUTO-CATEGORIZE
# ============================================

@router.post("/auto-categorize-all")
def auto_categorize_all():
    """Auto-categorize all uncategorized transactions"""
    try:
        with SessionLocal() as db:
            # Get uncategorized transactions
            transactions = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.category_id == None)\
                .all()
            
            categorized = 0
            patterns = {
                "SALAIRE": ("Revenus", "income", 0.95),
                "VIREMENT": ("Transfert", "transfer", 0.80),
                "UBER": ("Transport", "expense", 0.90),
                "RESTO": ("Alimentation", "expense", 0.85),
                "NETFLIX": ("Abonnements", "expense", 0.95),
                "SPOTIFY": ("Abonnements", "expense", 0.95),
                "AMAZON": ("Shopping", "expense", 0.85),
                "CARREFOUR": ("Alimentation", "expense", 0.90),
                "LOYER": ("Logement", "expense", 0.95),
                "EDF": ("Énergie", "expense", 0.95),
            }
            
            for trans in transactions:
                label_upper = (trans.label or "").upper()
                
                for pattern, (cat_name, cat_type, confidence) in patterns.items():
                    if pattern in label_upper:
                        # Find or create category
                        category = db.query(Category)\
                            .filter(Category.name == cat_name)\
                            .first()
                        
                        if not category:
                            category = Category(
                                name=cat_name,
                                type=cat_type,
                                is_system=True
                            )
                            db.add(category)
                            db.flush()
                        
                        trans.category_id = category.id
                        trans.confidence_score = confidence
                        categorized += 1
                        break
            
            db.commit()
            
            return JSONResponse(
                content={
                    "total_transactions": len(transactions),
                    "categorized": categorized,
                    "uncategorized": len(transactions) - categorized
                },
                headers=get_cors_headers()
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# GET CATEGORY STATISTICS
# ============================================

@router.get("/{category_id}/stats")
def get_category_stats(category_id: int, days: int = 30):
    """Get statistics for a category"""
    try:
        from datetime import date, timedelta
        
        with SessionLocal() as db:
            category = db.query(Category).filter(Category.id == category_id).first()
            
            if not category:
                raise HTTPException(404, "Category not found")
            
            # Date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get transactions
            transactions = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.category_id == category_id,
                    BankTransactionEnhanced.date >= start_date,
                    BankTransactionEnhanced.date <= end_date
                )\
                .all()
            
            total = sum(float(t.amount) for t in transactions)
            avg = total / len(transactions) if transactions else 0
            
            return JSONResponse(
                content={
                    "category_id": category_id,
                    "category_name": category.name,
                    "period_days": days,
                    "transaction_count": len(transactions),
                    "total_amount": round(total, 2),
                    "average_amount": round(avg, 2),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
