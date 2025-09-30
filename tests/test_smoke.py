
import pandas as pd
from app.analyzers import analyze_trial_balance

def test_smoke():
    df = pd.DataFrame([
        {"account": "701", "label": "VENTES", "debit": 0, "credit": 100000},
        {"account": "6061", "label": "ACHATS", "debit": 40000, "credit": 0},
        {"account": "641", "label": "SALAIRES", "debit": 20000, "credit": 0},
    ])
    res = analyze_trial_balance(df, turnover=100000)
    assert res.kpi.revenue == 100000
    assert res.tax.corporate_income_tax >= 0
