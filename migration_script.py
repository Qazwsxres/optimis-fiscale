"""
Migration Script: BankTransaction → BankTransactionEnhanced
Migrates old transactions to new enhanced schema
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DATABASE_URL
from app.models_extended import BankTransaction as OldTransaction
from app.models_banking import BankAccount, BankTransactionEnhanced, Category

def migrate_transactions():
    """
    Migrate old BankTransaction to BankTransactionEnhanced
    
    Steps:
    1. Create default bank account if none exists
    2. Create default categories
    3. Migrate all old transactions
    4. Auto-categorize based on patterns
    """
    
    print("="*60)
    print("🔄 NUMMA Migration: BankTransaction → BankTransactionEnhanced")
    print("="*60)
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as db:
        # Step 1: Create default account
        print("\n📦 Step 1: Creating default bank account...")
        
        default_account = db.query(BankAccount).filter(BankAccount.name == "Compte Principal").first()
        
        if not default_account:
            default_account = BankAccount(
                name="Compte Principal",
                bank_name="Banque Importée",
                account_type="checking",
                provider="manual",
                balance=0
            )
            db.add(default_account)
            db.commit()
            db.refresh(default_account)
            print(f"  ✅ Created default account (ID: {default_account.id})")
        else:
            print(f"  ℹ️  Default account already exists (ID: {default_account.id})")
        
        # Step 2: Create default categories
        print("\n📂 Step 2: Creating default categories...")
        
        default_categories = [
            ("Revenus", "income", "💰", "#10b981"),
            ("Alimentation", "expense", "🍽️", "#ef4444"),
            ("Transport", "expense", "🚗", "#f59e0b"),
            ("Logement", "expense", "🏠", "#8b5cf6"),
            ("Abonnements", "expense", "📱", "#ec4899"),
            ("Shopping", "expense", "🛍️", "#06b6d4"),
            ("Transfert", "transfer", "↔️", "#6b7280"),
            ("Autres", "expense", "📌", "#9ca3af"),
        ]
        
        category_map = {}
        
        for name, cat_type, icon, color in default_categories:
            cat = db.query(Category).filter(Category.name == name).first()
            
            if not cat:
                cat = Category(
                    name=name,
                    type=cat_type,
                    icon=icon,
                    color=color,
                    is_system=True
                )
                db.add(cat)
                db.flush()
                print(f"  ✅ Created category: {name}")
            else:
                print(f"  ℹ️  Category exists: {name}")
            
            category_map[name] = cat.id
        
        db.commit()
        
        # Step 3: Migrate transactions
        print("\n🔄 Step 3: Migrating transactions...")
        
        old_transactions = db.query(OldTransaction).all()
        migrated_count = 0
        skipped_count = 0
        
        print(f"  Found {len(old_transactions)} old transactions to migrate")
        
        for old_trans in old_transactions:
            # Check if already migrated (by date + amount + label)
            existing = db.query(BankTransactionEnhanced).filter(
                BankTransactionEnhanced.date == old_trans.date,
                BankTransactionEnhanced.amount == old_trans.amount,
                BankTransactionEnhanced.label == old_trans.label
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create enhanced transaction
            new_trans = BankTransactionEnhanced(
                account_id=default_account.id,
                date=old_trans.date,
                label=old_trans.label,
                raw_label=old_trans.label,
                amount=old_trans.amount,
                balance=old_trans.balance,
                sub_category=old_trans.category
            )
            
            # Auto-categorize
            if old_trans.label:
                label_upper = old_trans.label.upper()
                
                patterns = {
                    "SALAIRE": "Revenus",
                    "VIREMENT": "Transfert",
                    "UBER": "Transport",
                    "RESTO": "Alimentation",
                    "NETFLIX": "Abonnements",
                    "SPOTIFY": "Abonnements",
                    "AMAZON": "Shopping",
                    "CARREFOUR": "Alimentation",
                }
                
                for pattern, category_name in patterns.items():
                    if pattern in label_upper:
                        new_trans.category_id = category_map.get(category_name)
                        new_trans.confidence_score = 0.85
                        break
            
            db.add(new_trans)
            migrated_count += 1
            
            if migrated_count % 100 == 0:
                print(f"  ⏳ Migrated {migrated_count} transactions...")
        
        db.commit()
        
        print(f"\n✅ Migration complete!")
        print(f"  - Migrated: {migrated_count}")
        print(f"  - Skipped (duplicates): {skipped_count}")
        print(f"  - Total: {len(old_transactions)}")
        
        # Step 4: Statistics
        print("\n📊 Step 4: Migration statistics...")
        
        total_enhanced = db.query(BankTransactionEnhanced).count()
        categorized = db.query(BankTransactionEnhanced).filter(
            BankTransactionEnhanced.category_id != None
        ).count()
        
        categorization_rate = (categorized / total_enhanced * 100) if total_enhanced > 0 else 0
        
        print(f"  - Total enhanced transactions: {total_enhanced}")
        print(f"  - Categorized: {categorized}")
        print(f"  - Categorization rate: {categorization_rate:.1f}%")
        
    print("\n" + "="*60)
    print("✅ Migration completed successfully!")
    print("="*60)

if __name__ == "__main__":
    try:
        migrate_transactions()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
